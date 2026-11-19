"""用真实已完成记录检查审计能否拒绝篡改；不修改磁盘原始记录。"""
from copy import deepcopy
import json
import unittest
from noisyloop.design import ROOT
from noisyloop.audit import audit


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=next(p for p in (ROOT/'tasks').glob('*/result.json')
                  if json.loads(p.read_text())['item']['arm']=='hybrid')
        cls.result=json.loads(path.read_text())

    def test_real_record_passes(self):
        self.assertTrue(audit(self.result,self.result['item'])['passed'])

    def test_changed_projection_is_rejected(self):
        value=deepcopy(self.result)
        value['attempts'][0]['projection_seed']+=1
        with self.assertRaises(AssertionError):
            audit(value,value['item'])

    def test_original_values_in_request_are_rejected(self):
        value=deepcopy(self.result)
        value['decisions'][0]['event']['request']['messages'][1]['content']+=' original_values_leak'
        with self.assertRaises(AssertionError):
            audit(value,value['item'])


if __name__=='__main__':
    unittest.main()
