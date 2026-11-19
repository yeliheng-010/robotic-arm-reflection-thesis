"""低成本模拟边界：成功停止，非法选择不执行，传输失败保留。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from worker import rollout


class WorkerTests(unittest.TestCase):
    def test_initial_success_does_not_observe_or_call(self):
        with tempfile.TemporaryDirectory() as folder,patch('worker.observe',side_effect=AssertionError('extra observation')):
            t=rollout({'mechanism':'outlier'},{'success':True},directory=Path(folder)/'t',method='base_latest')
        self.assertEqual((1,0,0),(len(t['attempts']),len(t['decisions']),t['extra_observations']))

    def test_invalid_response_never_executes_action(self):
        d={'selected':None,'invalid':'bad JSON'}
        with tempfile.TemporaryDirectory() as folder,patch('worker.observe',return_value={'extra_cost':2}),\
             patch('worker.decide',return_value=d),patch('worker.attempt',side_effect=AssertionError('fallback')):
            t=rollout({},dict(success=False),directory=Path(folder)/'t',method='base_latest')
        self.assertFalse(t['success'])
        self.assertEqual(2,t['extra_observations'])

    def test_transport_failure_does_not_create_completed_result(self):
        with tempfile.TemporaryDirectory() as folder,patch('worker.observe',return_value={'extra_cost':2}),\
             patch('worker.decide',return_value={'selected':None,'service_failure':True}):
            directory=Path(folder)/'t'
            with self.assertRaises(AssertionError):
                rollout({},dict(success=False),directory=directory,method='base_latest')
            self.assertTrue((directory/'progress.json').exists())
            self.assertFalse((directory/'result.json').exists())


if __name__=='__main__':
    unittest.main()
