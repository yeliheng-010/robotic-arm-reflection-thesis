import unittest
from model_grasp_gpu_v3.prompt import pack, messages
from model_grasp_intent_v1.test_adapters import request
from model_grasp_intent_v1.contract import CHOICES
from model_grasp_intent_v1.model import parse
import json


class PromptTests(unittest.TestCase):
    def test_types_explicit_without_changing_legal_values(self):
        result = pack(request())
        spec = result['actions'][0]['args_spec']
        self.assertEqual('object',spec.get('type'))
        self.assertEqual(set(CHOICES),set(spec['required']))
        for key, values in CHOICES.items():
            self.assertEqual(list(values),spec['properties'][key]['enum'])
        self.assertEqual('string',spec['properties']['region']['type'])
        self.assertEqual('integer',spec['properties']['tilt_deg']['type'])

    def test_explains_scalar_selection_without_filling_answer(self):
        text = messages(pack(request()))[0]['content']
        self.assertIn('每个字段只选一个',text)
        self.assertIn('不得复制整个枚举列表',text)

    def test_recorded_array_shaped_error_still_rejected(self):
        response = dict(finish_reason='stop',text=json.dumps(dict(action=dict(id='PROPOSE_GRASP',args=CHOICES))))
        with self.assertRaises(ValueError):
            parse(response)
