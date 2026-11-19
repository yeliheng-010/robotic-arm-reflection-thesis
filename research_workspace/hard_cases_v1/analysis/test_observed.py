"""真实干预记录的审计反篡改测试，原始文件保持只读。"""
from copy import deepcopy
import json
import unittest
from hardstudy.design import ROOT
from hardstudy.qualify import audit


class ObservedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=next(p for p in (ROOT/'qualification').glob('*/result.json')
                  if 'grasp_bias' in str(p) and (p.parent/'summary.json').exists())
        cls.value=json.loads(path.read_text())

    def test_actual_control_and_intervention(self):
        audit(self.value,self.value['item'])

    def test_changed_bias_specification_is_rejected(self):
        value=deepcopy(self.value)
        value['item']['injection']['grasp'][0]+=.001
        with self.assertRaises(AssertionError):
            audit(value,value['item'])

    def test_intervention_mislabeled_as_control_is_rejected(self):
        value=deepcopy(self.value)
        value['steps'][1]['intervention_enabled']=False
        with self.assertRaises(AssertionError):
            audit(value,value['item'])

    def test_feedback_tampering_is_rejected(self):
        value=deepcopy(self.value)
        value['steps'][1]['feedback']['evidence']['unexpected_truth']=1
        with self.assertRaises(AssertionError):
            audit(value,value['item'])


if __name__=='__main__':
    unittest.main()
