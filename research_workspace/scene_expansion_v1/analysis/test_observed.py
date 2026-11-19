"""真实资格记录的反篡改检查，不更改磁盘原始数据。"""
from copy import deepcopy
import json
import unittest
from expand.design import ROOT
from expand.qualify import audit


class ObservedAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=next(p for p in (ROOT/'qualification').glob('*/result.json')
                  if (p.parent/'summary.json').exists())
        cls.value=json.loads(path.read_text())

    def test_real_control_pair_passes(self):
        audit(self.value,self.value['item'])

    def test_success_tampering_is_rejected(self):
        value=deepcopy(self.value)
        value['steps'][-1]['success']=not value['steps'][-1]['success']
        with self.assertRaises(AssertionError):
            audit(value,value['item'])

    def test_feedback_tampering_is_rejected(self):
        value=deepcopy(self.value)
        value['steps'][-1]['feedback']['evidence']['unauthorized_field']=1
        with self.assertRaises(AssertionError):
            audit(value,value['item'])


if __name__=='__main__':
    unittest.main()
