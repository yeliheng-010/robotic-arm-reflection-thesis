import os
import sys
import unittest
from types import SimpleNamespace

import mujoco
import numpy as np


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "manipulator_grasp"))
sys.path.insert(0, os.path.join(ROOT, "graspnet-baseline", "models"))
sys.path.insert(0, os.path.join(ROOT, "graspnet-baseline", "dataset"))
sys.path.insert(0, os.path.join(ROOT, "graspnet-baseline", "utils"))
sys.path.insert(0, ROOT)

from graspnetAPI import Grasp, GraspGroup
from grasp_process import (
    _minmax,
    camera_calibration_from_env,
    generate_geometric_topdown_grasp,
    get_and_process_data,
    rank_grasp_candidates,
    robust_depth_at_pixel,
)
from main_vlm import _resolve_scene_body_id


TOP_DOWN_ROTATION = np.array(
    [
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
        [1.0, 0.0, 0.0],
    ]
)


def make_grasp(score, translation, rotation=TOP_DOWN_ROTATION, width=0.04):
    grasp_array = np.concatenate(
        [
            np.asarray([score, width, 0.02, 0.02], dtype=np.float64),
            np.asarray(rotation, dtype=np.float64).reshape(-1),
            np.asarray(translation, dtype=np.float64),
            np.asarray([-1.0], dtype=np.float64),
        ]
    )
    return Grasp(grasp_array)


class GraspPipelineTests(unittest.TestCase):
    def test_minmax_handles_constant_values(self):
        np.testing.assert_allclose(_minmax([0.2, 0.2]), [0.5, 0.5])

    def test_robust_depth_rejects_single_pixel_outlier(self):
        depth = np.ones((9, 9), dtype=np.float32)
        depth[4, 4] = 9.0
        self.assertAlmostEqual(robust_depth_at_pixel(depth, 4, 4, win=2), 1.0)

    def test_target_aware_sampling_keeps_context_and_expected_size(self):
        color = np.zeros((30, 30, 3), dtype=np.uint8)
        depth = np.ones((30, 30), dtype=np.float32)
        mask = np.zeros((30, 30), dtype=np.uint8)
        mask[10:20, 10:20] = 255

        end_points, target_cloud, scene_cloud, _, _ = get_and_process_data(
            color,
            depth,
            mask,
            num_points=1000,
            target_ratio=0.6,
        )

        self.assertEqual(tuple(end_points["point_clouds"].shape), (1, 1000, 3))
        self.assertEqual(len(target_cloud.points), 100)
        self.assertEqual(len(scene_cloud.points), 900)

    def test_ranking_filters_off_target_and_non_vertical_grasps(self):
        height = width = 100
        focal = height / (2.0 * np.tan(np.pi / 8.0))
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[35:65, 35:65] = 1
        depth = np.ones((height, width), dtype=np.float32)

        ys, xs = np.nonzero(mask)
        target_points = np.column_stack(
            [
                (xs - width / 2.0) / focal,
                (ys - height / 2.0) / focal,
                np.ones_like(xs),
            ]
        ).astype(np.float32)

        valid = make_grasp(0.8, [0.0, 0.0, 1.0])
        off_target = make_grasp(0.99, [0.35, 0.0, 1.0])
        side_approach = make_grasp(0.99, [0.0, 0.0, 1.0], rotation=np.eye(3))
        group = GraspGroup()
        group.add(valid)
        group.add(off_target)
        group.add(side_approach)

        ranked = rank_grasp_candidates(group, target_points, mask, depth)
        self.assertEqual(len(ranked), 1)
        np.testing.assert_allclose(ranked[0][0].translation, valid.translation)

    def test_geometric_backend_uses_short_axis_and_valid_width(self):
        xs = np.linspace(-0.10, 0.10, 50)
        ys = np.linspace(-0.02, 0.02, 20)
        grid_x, grid_y = np.meshgrid(xs, ys)
        points = np.column_stack(
            [grid_x.ravel(), grid_y.ravel(), np.ones(grid_x.size)]
        )

        group = generate_geometric_topdown_grasp(points)
        self.assertEqual(len(group), 1)
        grasp = group[0]
        np.testing.assert_allclose(grasp.rotation_matrix[:, 0], [0, 0, 1], atol=1e-6)
        self.assertLessEqual(grasp.width, 0.08)
        self.assertGreaterEqual(grasp.width, 0.02)

    def test_runtime_camera_calibration_matches_scene_camera(self):
        scene_path = os.path.join(
            ROOT, "manipulator_grasp", "assets", "scenes", "scene.xml"
        )
        model = mujoco.MjModel.from_xml_path(scene_path)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        env = SimpleNamespace(mj_model=model, mj_data=data, height=640, width=640)

        pose, intrinsics = camera_calibration_from_env(env)
        np.testing.assert_allclose(pose.t, [0.85, 0.6, 1.9], atol=1e-6)
        expected_focal = 640.0 / (2.0 * np.tan(np.deg2rad(58.0) / 2.0))
        self.assertAlmostEqual(intrinsics[0], expected_focal)
        self.assertAlmostEqual(intrinsics[1], expected_focal)
        self.assertAlmostEqual(intrinsics[2], 320.0)
        self.assertAlmostEqual(intrinsics[3], 320.0)

    def test_open_vocabulary_name_maps_to_scene_body(self):
        scene_path = os.path.join(
            ROOT, "manipulator_grasp", "assets", "scenes", "scene.xml"
        )
        model = mujoco.MjModel.from_xml_path(scene_path)
        data = mujoco.MjData(model)
        env = SimpleNamespace(mj_model=model, mj_data=data)
        body_id = _resolve_scene_body_id(env, "yellow duck")
        self.assertGreaterEqual(body_id, 0)
        self.assertEqual(
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id), "Duck"
        )

    def test_sorting_scene_contains_fixed_receptacles_and_free_props(self):
        scene_path = os.path.join(
            ROOT, "manipulator_grasp", "assets", "scenes", "scene.xml"
        )
        model = mujoco.MjModel.from_xml_path(scene_path)

        fixed_bodies = {"SortingTray", "BlueBin", "RedBin", "SafetyDivider"}
        movable_bodies = {
            "RedBlock",
            "GreenCylinder",
            "PurpleCapsule",
            "OrangeSphere",
        }
        for name in fixed_bodies | movable_bodies:
            self.assertGreaterEqual(
                mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name),
                0,
                msg=f"missing scene body: {name}",
            )

        free_joint_bodies = {
            mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, int(body_id))
            for joint_type, body_id in zip(model.jnt_type, model.jnt_bodyid)
            if joint_type == mujoco.mjtJoint.mjJNT_FREE
        }
        self.assertTrue(movable_bodies.issubset(free_joint_bodies))
        self.assertTrue(fixed_bodies.isdisjoint(free_joint_bodies))

        for bin_name, prefix in (("BlueBin", "blue_bin_"), ("RedBin", "red_bin_")):
            body_id = mujoco.mj_name2id(
                model, mujoco.mjtObj.mjOBJ_BODY, bin_name
            )
            geom_names = {
                mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
                for geom_id in np.flatnonzero(model.geom_bodyid == body_id)
            }
            self.assertEqual(
                geom_names,
                {
                    f"{prefix}floor",
                    f"{prefix}left_wall",
                    f"{prefix}right_wall",
                    f"{prefix}front_wall",
                    f"{prefix}back_wall",
                },
            )

    def test_sorting_props_settle_on_tabletop(self):
        scene_path = os.path.join(
            ROOT, "manipulator_grasp", "assets", "scenes", "scene.xml"
        )
        model = mujoco.MjModel.from_xml_path(scene_path)
        data = mujoco.MjData(model)
        for _ in range(750):
            mujoco.mj_step(model, data)

        for name in ("RedBlock", "GreenCylinder", "PurpleCapsule", "OrangeSphere"):
            body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, name)
            x, y, z = data.xpos[body_id]
            self.assertTrue(0.0 < x < 1.6, msg=f"{name} left table in x")
            self.assertTrue(0.0 < y < 1.2, msg=f"{name} left table in y")
            self.assertGreater(z, 0.74, msg=f"{name} fell through tabletop")
            self.assertLess(z, 0.90, msg=f"{name} did not settle")

    def test_sorting_aliases_resolve_to_expected_bodies(self):
        scene_path = os.path.join(
            ROOT, "manipulator_grasp", "assets", "scenes", "scene.xml"
        )
        model = mujoco.MjModel.from_xml_path(scene_path)
        env = SimpleNamespace(mj_model=model, mj_data=mujoco.MjData(model))
        aliases = {
            "red block": "RedBlock",
            "green cylinder": "GreenCylinder",
            "purple capsule": "PurpleCapsule",
            "blue bin": "BlueBin",
            "red bin": "RedBin",
            "sorting tray": "SortingTray",
        }
        for alias, expected in aliases.items():
            body_id = _resolve_scene_body_id(env, alias)
            self.assertGreaterEqual(body_id, 0)
            self.assertEqual(
                mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id),
                expected,
            )


if __name__ == "__main__":
    unittest.main()
