import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from worker import rollout


class WorkerTests(unittest.TestCase):
    def test_initial_success_never_observes(self):
        with tempfile.TemporaryDirectory() as folder,patch('worker.observe',side_effect=AssertionError('unexpected')):
            t=rollout({},dict(success=True),directory=Path(folder)/'t',method='adaptive')
        self.assertEqual((1,0),(len(t['attempts']),t['extra_observations']))

    def test_empty_menu_does_not_execute(self):
        with tempfile.TemporaryDirectory() as folder,patch('worker.observe',return_value={'extra_cost':2}),\
             patch('worker.decide',return_value={'selected':None}),patch('worker.attempt',side_effect=AssertionError('unexpected')):
            t=rollout({},dict(success=False),directory=Path(folder)/'t',method='adaptive')
        self.assertEqual((1,1,2),(len(t['attempts']),len(t['decisions']),t['extra_observations']))


if __name__=='__main__':
    unittest.main()
