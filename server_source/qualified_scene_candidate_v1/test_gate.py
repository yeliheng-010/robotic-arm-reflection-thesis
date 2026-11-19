"""新入口的阻断和判定测试，不创建模型或渲染器。"""
import tempfile
import unittest
import mujoco
from qualified_scene_candidate_v1.guard import no_motion, UR5GraspEnv, require_no_motion
from qualified_scene_candidate_v1.checks import decision
from qualified_scene_candidate_v1.common import claim


class GateTests(unittest.TestCase):
    def test_integrator_is_blocked_before_native_call(self):
        with no_motion() as counts:
            for function in (mujoco.mj_step, mujoco.mj_step1, mujoco.mj_step2):
                with self.assertRaises(RuntimeError):
                    function(None, None)
            self.assertEqual(3, counts['integration'])

    def test_environment_step_is_blocked(self):
        with no_motion() as counts:
            with self.assertRaises(RuntimeError):
                UR5GraspEnv.step(None)
            self.assertEqual(1, counts['environment_step'])

    def test_empty_guard_has_zero_motion(self):
        with no_motion() as counts:
            require_no_motion(counts)
            self.assertTrue(all(value == 0 for value in counts.values()))

    def test_claim_is_exclusive(self):
        with tempfile.TemporaryDirectory() as folder:
            claim(folder, 'scene')
            with self.assertRaises(FileExistsError):
                claim(folder, 'scene')

    def test_all_static_gates_required(self):
        valid = dict(equalities=[dict(passed=True)], limits=[dict(passed=True)],
                     hits=[], finite=True, warnings=False)
        self.assertTrue(decision(**valid))
        changes = dict(equalities=[dict(passed=False)], limits=[dict(passed=False)],
                       hits=[dict(contact=True)], finite=False, warnings=True)
        for key, value in changes.items():
            self.assertFalse(decision(**dict(valid, **{key: value})), key)


if __name__ == '__main__':
    unittest.main(verbosity=2)
