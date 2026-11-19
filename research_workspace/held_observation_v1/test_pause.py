from types import SimpleNamespace
import unittest
from held_observation_v1.pause import execute,CaptureComplete


def fixture():
    env=SimpleNamespace(mj_data=SimpleNamespace(time=0.))
    def step(action):
        env.mj_data.time+=.1
    env.step=step
    values=(object(),env,[object(),object(),object()],[0.,.3,.3,.3],object(),.1)
    calls=[]
    def backend(*args):
        calls.append(args)
        for _ in range(9):
            env.step(None)
        return args[4]
    return env,values,calls,backend


class PauseTests(unittest.TestCase):
    def test_capture_without_changing_command_or_time(self):
        env,values,calls,backend=fixture()
        phases=[]
        with self.assertRaises(CaptureComplete):
            execute(backend,values,capture=lambda phase:phases.append((phase,env.mj_data.time)))
        self.assertEqual(1,len(calls))
        self.assertTrue(all(a is b for a,b in zip(values,calls[0])))
        self.assertEqual(['after_lift','before_release'],[p[0] for p in phases])
        self.assertAlmostEqual(.3,phases[0][1])
        self.assertAlmostEqual(.9,phases[1][1])

    def test_backend_failure_does_not_fabricate_final_capture(self):
        env,values,calls,backend=fixture()
        original=env.step
        def fail(*args):
            raise RuntimeError('backend failed')
        with self.assertRaisesRegex(RuntimeError,'backend failed'):
            execute(fail,values,capture=lambda phase:self.fail('Unexpected capture'))
        self.assertIs(original,env.step)
