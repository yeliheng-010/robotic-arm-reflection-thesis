import copy
import json
import unittest

from training.qlora.data import encode_example
from training.qlora.export_verified import verified_examples
from reflection.reflector import Parameters


class TemplateTokenizer:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        text = ''.join(m['role'] + ':' + m['content'] + '\n' for m in messages)
        return text + ('assistant:' if add_generation_prompt else '')

    def __call__(self, text, add_special_tokens=False):
        return {'input_ids': list(text.encode())}


class QLoRADataTests(unittest.TestCase):
    def example(self):
        p = Parameters()
        return {'instruction': '把方块放入箱子', 'fault': 'hidden_injection_label', 'records': [
            {'attempt': 1, 'parameters': p.to_dict(),
             'error': {'error_type': 'collision', 'message': 'contact', 'timestamp': 123,
                       'image_paths': ['/private/image.png']},
             'reflection': {'source': 'llm', 'cause': 'contact during transport', 'changes': {'lift_height': 0.45}}},
            {'attempt': 2, 'parameters': p.updated({'lift_height': 0.45}).to_dict(),
             'accepted': True, 'physical_success': True},
        ]}

    def test_export_excludes_unverified_and_mismatched_executions(self):
        good = self.example()
        self.assertEqual(len(list(verified_examples(good, 'x/result.json'))), 1)
        for field, value in [('accepted', False), ('physical_success', False), ('attempt', 4)]:
            bad = copy.deepcopy(good)
            bad['records'][1][field] = value
            self.assertEqual(list(verified_examples(bad, 'x')), [])
        bad = copy.deepcopy(good)
        bad['records'][1]['parameters']['lift_height'] = 0.35
        self.assertEqual(list(verified_examples(bad, 'x')), [])
        good['records'][0]['reflection']['source'] = 'rule'
        self.assertEqual(list(verified_examples(good, 'x')), [])

    def test_inputs_do_not_include_fault_labels_future_outcomes_or_private_paths(self):
        e = next(verified_examples(self.example(), 'x'))
        prompt = json.dumps(e['messages'][:-1])
        for private in ('hidden_injection_label', '/private/', 'physical_success', 'timestamp'):
            self.assertNotIn(private, prompt)

    def test_only_answer_tokens_are_supervised_and_overlength_is_rejected(self):
        messages = [{'role': r, 'content': s} for r, s in [('system', 'rules'), ('user', 'evidence'), ('assistant', '{"changes":{}}')]]
        encoded = encode_example(TemplateTokenizer(), messages, 1000)
        supervised = [t for t in encoded['labels'] if t != -100]
        self.assertEqual(bytes(supervised).decode(), '{"changes":{}}\n')
        with self.assertRaisesRegex(ValueError, 'no truncation'):
            encode_example(TemplateTokenizer(), messages, 5)


if __name__ == '__main__':
    unittest.main()
