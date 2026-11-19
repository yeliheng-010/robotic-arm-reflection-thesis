"""用真实 MjSpec 编译验证几何、惯性和方向，而非只验证配置字典。"""
import unittest
import mujoco
import numpy as np
from diversity.config import scenario, SOURCES, valid_layout
from diversity.scene import apply_scene, GEOMS

SCENE = 'manipulator_grasp/assets/scenes/scene.xml'


class SceneTests(unittest.TestCase):
    def test_clean_preserves_compiled_physics(self):
        original = mujoco.MjModel.from_xml_path(SCENE)
        spec = mujoco.MjSpec.from_file(SCENE)
        apply_scene(spec, scenario(61000, 'clean'))
        actual = spec.compile()
        for field in ('body_pos', 'body_quat', 'body_mass', 'body_inertia', 'geom_friction'):
            np.testing.assert_array_equal(getattr(original, field), getattr(actual, field))

    def test_randomized_values_reach_compiled_model(self):
        original = mujoco.MjModel.from_xml_path(SCENE)
        config = scenario(61000, 'medium')
        spec = mujoco.MjSpec.from_file(SCENE)
        apply_scene(spec, config)
        actual = spec.compile()
        for name in SOURCES:
            body, geom = actual.body(name), actual.geom(GEOMS[name])
            settings = config['bodies'][name]
            np.testing.assert_allclose(body.pos[:2], settings['xy'])
            np.testing.assert_allclose(body.mass, original.body(name).mass*settings['density_scale'])
            np.testing.assert_allclose(geom.friction[0],
                                       original.geom(GEOMS[name]).friction[0]*settings['friction_scale'])
        rotation = np.empty(9)
        mujoco.mju_quat2Mat(rotation, actual.body('PurpleCapsule').quat)
        self.assertLess(abs(rotation.reshape(3, 3)[2, 2]), 1e-6)

    def test_layout_constraints_across_seeds(self):
        for seed in range(61000, 61030):
            for level in ('light', 'medium', 'strong'):
                config = scenario(seed, level)
                self.assertTrue(valid_layout([config['bodies'][n]['xy'] for n in SOURCES]))


if __name__ == '__main__':
    unittest.main()
