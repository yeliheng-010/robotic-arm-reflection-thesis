import unittest
from copy import deepcopy
from model_grasp_gpu_v2.pack import pack
from model_grasp_intent_v1.test_adapters import request


class PackingTests(unittest.TestCase):
    def test_bounded_points_without_mutating_original(self):
        source = request()
        source['observation']['non_target_points_world'] = [[.123456789, .2, .3]]*256
        previous = deepcopy(source)
        result = pack(source)
        self.assertEqual(32,len(result['observation']['target_points_world']))
        self.assertEqual(96,len(result['observation']['non_target_points_world']))
        self.assertEqual(previous,source)
        self.assertEqual(source['actions'],result['actions'])
        self.assertEqual(source['budget'],result['budget'])
        self.assertEqual(.123457,result['observation']['non_target_points_world'][0][0])
