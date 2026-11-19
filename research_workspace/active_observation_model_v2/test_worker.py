"""成功空反馈、非法输出和服务错误必须遵守终止语义。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import worker
from am_policy import context
from test_policy import fixture


def decision(step,samples):
    return dict(selected=dict(id='a',state=step['state']),
        choices=[dict(context=context(step,samples,used=0))],
        observation=dict(extra_cost=0),invalid=None,service_failure=None)


class WorkerTests(unittest.TestCase):
    def test_success_none_feedback_completes_and_stops(self):
        step,samples=fixture()
        result=dict(step,index=2,success=True,feedback=None)
        with tempfile.TemporaryDirectory() as folder:
            with patch('worker.decide',return_value=decision(step,samples)) as decide:
                with patch('worker.attempt',return_value=result) as attempt:
                    out=worker.rollout({},step,directory=Path(folder)/'trace',method='fixed_first')
        self.assertEqual(('completed',True,2),(out['status'],out['success'],len(out['attempts'])))
        self.assertEqual(1,decide.call_count)
        self.assertEqual(1,attempt.call_count)

    def test_invalid_stops_without_execution(self):
        step,samples=fixture()
        invalid=dict(decision(step,samples),selected=None,invalid='bad JSON')
        with tempfile.TemporaryDirectory() as folder:
            with patch('worker.decide',return_value=invalid),patch('worker.attempt') as attempt:
                out=worker.rollout({},step,directory=Path(folder)/'trace',method='base_current')
        self.assertFalse(out['success'])
        self.assertEqual(1,len(out['attempts']))
        attempt.assert_not_called()

    def test_service_failure_leaves_progress_not_final(self):
        step,samples=fixture()
        failure=dict(decision(step,samples),selected=None,service_failure='timeout')
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder)/'trace'
            with patch('worker.decide',return_value=failure),self.assertRaises(AssertionError):
                worker.rollout({},step,directory=directory,method='base_current')
            self.assertTrue((directory/'progress.json').exists())
            self.assertFalse((directory/'result.json').exists())


if __name__=='__main__':
    unittest.main()
