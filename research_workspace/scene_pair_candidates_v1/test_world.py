import unittest
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from world_candidates import generate


def camera(angle):
    a = np.deg2rad(angle)
    cv = np.array([[1.,0,0],[0,np.cos(a),-np.sin(a)],[0,np.sin(a),np.cos(a)]])
    return dict(rotation=(cv@np.diag([1.,-1.,-1.])).tolist(), position=[.4,.6,1.7])


class WorldTests(unittest.TestCase):
    def test_rank_changes_only_angle_frame_and_returns_real_pose(self):
        from candidate_rank import ranking
        from grasp_process import GraspGroup
        config = camera(45)
        rotation = np.asarray(config['rotation'])@np.diag([1.,-1.,-1.])
        data = np.zeros((1,17))
        actual = rotation.T @ np.diag([1.,-1.,-1.]) @ np.array([[0.,1,0],[0,0,1],[1,0,0]])
        data[0,4:13], data[0,13:16] = actual.ravel(), [.1,.2,1.]
        group = GraspGroup(data)
        def check(proxy):
            np.testing.assert_allclose([0.,0.,1.], proxy[0].rotation_matrix[:,0], atol=1e-12)
            np.testing.assert_array_equal(group.translations, proxy.translations)
            return [(proxy[0], 1., {})]
        ranked = ranking(check, {'active':True}, config)(group)
        np.testing.assert_array_equal(group.grasp_group_array[0], ranked[0][0].grasp_array)

    def test_approach_is_world_down_for_tilted_camera(self):
        rng = np.random.default_rng(17)
        world = rng.uniform([.9,.5,.77], [1.,.54,.79], (400,3))
        for angle in (25,65):
            config = camera(angle)
            rotation = np.asarray(config['rotation'])@np.diag([1.,-1.,-1.])
            points = (world-config['position'])@rotation
            group = generate(points, config)
            for grasp in group:
                np.testing.assert_allclose([0.,0.,-1.], rotation@grasp.rotation_matrix[:,0], atol=1e-12)
                np.testing.assert_allclose(np.eye(3), grasp.rotation_matrix.T@grasp.rotation_matrix, atol=1e-12)
                self.assertAlmostEqual(1., np.linalg.det(grasp.rotation_matrix))
                self.assertLessEqual(grasp.width, .08)

    def test_median_center_is_independent_of_camera_and_input_unchanged(self):
        world = np.random.default_rng(23).uniform([.9,.5,.77], [1.,.54,.79], (400,3))
        for angle in (25,65):
            config = camera(angle)
            rotation = np.asarray(config['rotation'])@np.diag([1.,-1.,-1.])
            points = (world-config['position'])@rotation
            before = points.copy()
            group = generate(points, config)
            np.testing.assert_allclose(np.median(world,axis=0), rotation@group[0].translation+config['position'], atol=1e-12)
            np.testing.assert_array_equal(before, points)
