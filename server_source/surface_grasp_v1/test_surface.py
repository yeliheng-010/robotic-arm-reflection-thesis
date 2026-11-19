import unittest
import numpy as np
from surface_grasp_v1.geometry import anchors,orientations
from surface_grasp_v1.candidates import build


def cloud():
    x,y=np.meshgrid(np.linspace(.75,.85,31),np.linspace(.38,.42,17))
    return np.column_stack((x.ravel(),y.ravel(),np.full(x.size,.79)))


class SurfaceTests(unittest.TestCase):
    def test_surface_normals_face_camera(self):
        rows=anchors(cloud(),[.8,.4,1.8])
        self.assertEqual(12,len(rows))
        for row in rows:
            self.assertAlmostEqual(.79,row['point'][2])
            self.assertGreater(np.dot(row['normal'],[0,0,1]),.99)

    def test_basis_is_right_handed_and_closing_can_rotate(self):
        rows=orientations([0,0,1],[1,0,0])
        self.assertGreaterEqual(len(rows),24)
        for row in rows:
            rotation=np.asarray(row['rotation'])
            np.testing.assert_allclose(np.eye(3),rotation.T@rotation,atol=1e-12)
            self.assertAlmostEqual(1.,np.linalg.det(rotation))
        top=[r for r in rows if r['family']=='normal']
        self.assertGreater(len({tuple(np.round(np.array(r['rotation'])[:,1],8)) for r in top}),2)

    def test_budget_and_original_safety_bounds(self):
        result=build(cloud(),[[.9,.4,.8]],nominal=[.8,.4,.77],camera=[.8,.4,1.8])
        rows=result['catalogue']
        self.assertGreater(len(rows),0)
        self.assertLessEqual(len(rows),512)
        for row in rows:
            pose=np.asarray(row['proposal']['pose'])
            self.assertLessEqual(np.linalg.norm(pose[:3,3]-[.8,.4,.77]),.05)
            self.assertLessEqual(row['proposal']['required_width_m'],.08)
            self.assertFalse(row['proposal']['full_path_verified'])

    def test_permutation_does_not_change_candidates(self):
        kwargs=dict(nominal=[.8,.4,.77],camera=[.8,.4,1.8])
        a=build(cloud(),[[.9,.4,.8]],**kwargs)
        b=build(cloud()[::-1],[[.9,.4,.8]],**kwargs)
        self.assertGreater(len(a['catalogue']),0)
        self.assertEqual(a,b)

    def test_previous_poses_not_rechecked(self):
        kwargs=dict(nominal=[.8,.4,.77],camera=[.8,.4,1.8])
        first=build(cloud(),[[.9,.4,.8]],**kwargs)
        self.assertGreater(len(first['catalogue']),0)
        old=[r['proposal']['pose'] for r in first['catalogue']]
        second=build(cloud(),[[.9,.4,.8]],previous=old,**kwargs)
        old_keys={tuple(np.round(np.array(p).ravel(),12)) for p in old}
        self.assertFalse(any(tuple(np.round(np.array(r['proposal']['pose']).ravel(),12)) in old_keys
                             for r in second['catalogue']))

    def test_invalid_cloud_rejected(self):
        with self.assertRaises(ValueError):
            anchors(np.full((64,3),np.nan),[0,0,1])
