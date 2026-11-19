"""真实rollout循环的物理/观测预算独立验证。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sensor
import worker
from test_sensor import fixture


class RolloutTests(unittest.TestCase):
    def run_probe(self,mode,*,mechanism='occlusion',success_at=99):
        step,item=fixture(mechanism)
        step['success']=False
        count=[]
        def attempt(current,state,*,directory,index):
            count.append(index)
            return dict(step,index=index,state=state,success=index==success_at)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(worker,'attempt',attempt),patch.object(sensor,'OCCLUSION',1.):
                result=worker.rollout(item,([step],[]),directory=Path(directory)/'episode',mode=mode)
        return count,result

    def test_extra_observations_do_not_add_physical_attempts(self):
        count,result=self.run_probe('reobserve')
        self.assertEqual([2,3],count)
        self.assertEqual(2,result['extra_observations'])
        self.assertEqual(3,len(result['attempts']))

    def test_success_stops_execution(self):
        count,result=self.run_probe('no_extra',success_at=2)
        self.assertEqual([2],count)
        self.assertTrue(result['success'])
        self.assertEqual(0,result['extra_observations'])

    def test_side_effect_qualification_has_separate_budget(self):
        count,result=self.run_probe('rule',mechanism='side_effect')
        self.assertEqual([2,3,4],count)
        self.assertEqual(0,result['extra_observations'])


if __name__=='__main__':
    unittest.main()
