"""验证模型输出进入执行器前的关键边界。"""
import unittest
from reflection.reflector import Parameters
from flashnext.client import check_response, parse_correction


class ClientTests(unittest.TestCase):
    def response(self, text, **changes):
        result = {'model': 'qwen3.8-flash-next', 'choices': [
            {'finish_reason': 'stop', 'message': {'content': text}}]}
        result.update(changes)
        return result

    def test_model_identity_and_truncation(self):
        with self.assertRaises(ValueError):
            check_response(self.response('{}', model='different-model'))
        reply = self.response('{"cause":"collision","changes":{"lift_height":0.45}}')
        reply['choices'][0]['finish_reason'] = 'length'
        with self.assertRaises(ValueError):
            check_response(reply)

    def test_rejects_illegal_unchanged_and_unavailable_correction(self):
        values = ('{"closure":1}', '{"lift_height":0.35}',
                  '{"lift_height":NaN}', '{"candidate_index":2}')
        for changes in values:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_correction('{"cause":"evidence","changes":'+changes+'}',
                                 Parameters(), candidate_count=2)

    def test_valid_changes_apply_as_absolute_values(self):
        current = Parameters(grasp_offset=(0.1, 0, 0))
        raw = '{"cause":"correct residual","changes":{"grasp_offset":[0.02,0,0]}}'
        text = check_response(self.response(raw))
        answer = parse_correction(text, current)
        self.assertEqual('llm', answer.source)
        self.assertEqual((0.02, 0, 0), current.updated(answer.changes).grasp_offset)


if __name__ == '__main__':
    unittest.main()
