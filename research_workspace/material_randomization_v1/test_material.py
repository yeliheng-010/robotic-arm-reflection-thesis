import unittest
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from cl_design import SCENE
from material import sample, apply, validate, PADS


def compile_settings(settings):
    spec = mujoco.MjSpec.from_file(str(SCENE))
    apply(spec, settings)
    return spec.compile()


class MaterialTests(unittest.TestCase):
    def test_baseline_leaves_original_model_unchanged(self):
        expected = mujoco.MjSpec.from_file(str(SCENE)).compile()
        actual = compile_settings(sample(42, 'baseline'))
        for name in ('body_mass', 'body_inertia', 'geom_friction', 'geom_size', 'geom_priority', 'actuator_forcerange'):
            np.testing.assert_array_equal(getattr(expected, name), getattr(actual, name))

    def test_determinism_and_invalid_ranges(self):
        self.assertEqual(sample(42, 'varied_noisy'), sample(42, 'varied_noisy'))
        settings = sample(42, 'varied_noisy')
        settings['pad_sliding_multiplier'] = 0.
        with self.assertRaises(AssertionError):
            validate(settings)

    def test_mass_and_inertia_scale_together_without_shape_change(self):
        settings = sample(42, 'varied_noisy')
        base, varied = compile_settings({}), compile_settings(settings)
        for name, scale in settings['density_multipliers'].items():
            bid = int(base.geom_bodyid[base.geom(name).id])
            np.testing.assert_allclose(base.body_mass[bid] * scale, varied.body_mass[bid])
            np.testing.assert_allclose(base.body_inertia[bid] * scale, varied.body_inertia[bid])
        np.testing.assert_array_equal(base.geom_size, varied.geom_size)
        np.testing.assert_array_equal(base.actuator_forcerange, varied.actuator_forcerange)
        for name in PADS:
            gid = base.geom(name).id
            expected = base.geom_friction[gid].copy()
            expected[0] *= settings['pad_sliding_multiplier']
            np.testing.assert_allclose(expected, varied.geom_friction[gid])

    def test_high_priority_pad_determines_effective_contact(self):
        xml = '''<mujoco><worldbody>
          <geom type="plane" size="1 1 .1" priority="1" friction=".455 .005 .0001" condim="3"/>
          <body pos="0 0 .09"><freejoint/>
            <geom type="sphere" size=".1" priority="0" friction="1 .03 .002" condim="4"/>
          </body></worldbody></mujoco>'''
        model = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(model)
        mujoco.mj_forward(model, data)
        self.assertGreater(data.ncon, 0)
        self.assertEqual(3, data.contact[0].dim)
        np.testing.assert_allclose([.455, .455, .005, .0001, .0001], data.contact[0].friction)


if __name__ == '__main__':
    unittest.main()
