"""无人值守阶段失败必须阻断，服务退出与超时必须可见。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import orchestrator
import slurm_control


class ControlTests(unittest.TestCase):
    def test_failed_slurm_job_rejected(self):
        process=Mock()
        process.poll.return_value=None
        with patch.object(slurm_control,'active',return_value=False),patch.object(slurm_control,'records',
                return_value=[dict(state='FAILED',exit_code='1:0')]):
            with self.assertRaises(AssertionError):
                slurm_control.wait_job('123',service=process,deadline=float('inf'))

    def test_service_death_stops_wait(self):
        process=Mock()
        process.poll.return_value=1
        with self.assertRaises(AssertionError):
            slurm_control.wait_job('123',service=process,deadline=float('inf'))

    def test_timeout_stops_wait(self):
        process=Mock()
        process.poll.return_value=None
        with self.assertRaises(AssertionError):
            slurm_control.wait_job('123',service=process,deadline=0)

    def test_failed_stage_never_submits_next(self):
        process=Mock()
        process.poll.return_value=None
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(orchestrator,'ROOT',Path(directory)),patch.object(orchestrator,'wait_ready',return_value={}):
                with patch.object(orchestrator,'submit',return_value='123') as submit:
                    with patch.object(orchestrator,'wait_job',side_effect=AssertionError('failed')):
                        with self.assertRaises(AssertionError):
                            orchestrator.run_stages(process,{},dict(status='running'))
        self.assertEqual(1,submit.call_count)

    def test_cancel_only_explicit_owned_active_children(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(slurm_control,'ROOT',Path(directory)),patch.object(slurm_control,'active',return_value=True):
                with patch.object(slurm_control.subprocess,'run',return_value=Mock(returncode=0)) as run:
                    slurm_control.cancel_owned(dict(preflight='1',service='2',smoke='3'))
        self.assertEqual(['scancel','3'],run.call_args.args[0])


if __name__=='__main__':
    unittest.main()
