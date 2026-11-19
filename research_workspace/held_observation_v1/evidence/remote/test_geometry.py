import unittest
import numpy as np
from held_observation_v1.geometry import estimate


def clouds():
    rng=np.random.default_rng(52)
    direction=rng.normal(size=(2400,3))
    direction/=np.linalg.norm(direction,axis=1)[:,None]
    x=rng.uniform(-.055,.055,2400)
    side=direction.copy()
    side[:,0]=0
    side/=np.linalg.norm(side,axis=1)[:,None]
    points=.025*side+np.column_stack((x,np.zeros((2400,2))))
    caps=.025*direction+np.column_stack((.055*np.sign(direction[:,0]),np.zeros((2400,2))))
    points=np.vstack((points,caps))
    center=np.array([.8,.4,.9])
    a=points[points[:,2]>0]+center
    b=points[points[:,1]>0]+center
    return [a+rng.normal(0,.0005,a.shape),b+rng.normal(0,.0005,b.shape)],center


class GeometryTests(unittest.TestCase):
    def test_center_and_axis_from_partial_views(self):
        views,center=clouds()
        value=estimate(views,np.eye(4))
        self.assertTrue(value['quality_passed'])
        self.assertLess(np.linalg.norm(np.array(value['center_world_m'])-center),.003)
        self.assertGreater(abs(value['axis_world'][0]),.99)
        self.assertFalse(value['release_authorized'])
        self.assertFalse(value['roll_observable'])

    def test_tcp_coordinates_transform_without_truth(self):
        views,center=clouds()
        tcp=np.eye(4);tcp[:3,3]=[.2,-.1,.3]
        value=estimate(views,tcp)
        self.assertTrue(value['quality_passed'])
        np.testing.assert_allclose(np.array(value['center_world_m'])-tcp[:3,3],value['center_tcp_m'],atol=1e-12)

    def test_single_view_is_insufficient(self):
        views,_=clouds()
        self.assertFalse(estimate(views[:1],np.eye(4))['quality_passed'])

    def test_flat_surface_is_not_a_capsule_pose(self):
        x,y=np.meshgrid(np.linspace(-.05,.05,20),np.linspace(-.02,.02,20))
        flat=np.column_stack((x.ravel(),y.ravel(),np.zeros(x.size)))
        self.assertFalse(estimate([flat,flat],np.eye(4))['quality_passed'])

    def test_nonfinite_input_is_rejected(self):
        bad=np.full((300,3),np.nan)
        self.assertFalse(estimate([bad,bad],np.eye(4))['quality_passed'])

    def test_rotated_capsule_axis_is_recovered(self):
        views,center=clouds()
        angle=np.deg2rad(55)
        rotation=np.array([[np.cos(angle),0,np.sin(angle)],[0,1,0],[-np.sin(angle),0,np.cos(angle)]])
        rotated=[(p-center)@rotation.T+center for p in views]
        value=estimate(rotated,np.eye(4))
        self.assertTrue(value['quality_passed'])
        self.assertGreater(abs(np.dot(value['axis_world'],rotation[:,0])),.99)

    def test_conflicting_views_are_rejected(self):
        views,_=clouds()
        views[1]=views[1]+np.array([.05,0,0])
        self.assertFalse(estimate(views,np.eye(4))['quality_passed'])
