import unittest
from types import SimpleNamespace
import mujoco
import numpy as np
from qualified_task_v1.snapshot import isolated
from qualified_task_v1.integrity import fingerprint, unchanged

XML = '''<mujoco><worldbody><camera name="cam" pos="0 0 2"/>
<body pos="0 0 1"><freejoint/><geom type="sphere" size=".1"/></body>
</worldbody></mujoco>'''


def environment():
    model = mujoco.MjModel.from_xml_string(XML)
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return SimpleNamespace(mj_model=model, mj_data=data, width=640, height=640, fovy=np.pi/4)


class SnapshotTests(unittest.TestCase):
    def test_stale_derived_caches_stay_stale(self):
        env, audit = environment(), {}
        env.mj_data.qpos[0] += .123
        before = fingerprint(env)
        with isolated(env, audit) as snapshot:
            self.assertNotEqual(env.mj_data.xpos[1, 0], snapshot.mj_data.xpos[1, 0])
            np.testing.assert_array_equal(env.mj_data.qpos, snapshot.mj_data.qpos)
            snapshot.mj_model.cam_pos[0, 0] += 1
            snapshot.mj_data.ctrl[:] = 0
        self.assertTrue(audit['passed'])
        unchanged(before, fingerprint(env))

    def test_exception_still_checks_source(self):
        env, audit = environment(), {}
        with self.assertRaisesRegex(ValueError, 'injected'):
            with isolated(env, audit):
                raise ValueError('injected')
        self.assertTrue(audit['passed'])

    def test_live_forward_is_forbidden(self):
        env, audit = environment(), {}
        with self.assertRaisesRegex(RuntimeError, 'Live forward'):
            with isolated(env, audit):
                mujoco.mj_forward(env.mj_model, env.mj_data)
        self.assertTrue(audit['passed'])

    def test_integration_is_forbidden(self):
        env, audit = environment(), {}
        with self.assertRaisesRegex(RuntimeError, 'Integration'):
            with isolated(env, audit) as snapshot:
                mujoco.mj_step(snapshot.mj_model, snapshot.mj_data)
        self.assertTrue(audit['passed'])

    def test_detects_live_derived_mutation(self):
        env = environment()
        with self.assertRaisesRegex(AssertionError, 'data'):
            with isolated(env, {}):
                env.mj_data.geom_xpos[0, 0] += .1


if __name__ == '__main__':
    unittest.main()
