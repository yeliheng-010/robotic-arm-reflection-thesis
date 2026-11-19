"""试训不得遗漏尾批、截断答案或使用测试集调参。"""
import unittest
from stability.sft_data import encode, epoch_groups, validate_rows


class Tokenizer:
    def apply_chat_template(self, messages, **kwargs):
        return 'prompt:' if len(messages) == 2 else 'prompt:answer!'

    def __call__(self, text, **kwargs):
        return {'input_ids': list(text.encode())}


class SftDataTests(unittest.TestCase):
    def test_masks_prompt_and_preserves_entire_answer(self):
        row = encode(Tokenizer(), [{}, {}, {}], max_length=50)
        self.assertEqual([-100]*7+list(b'answer!'), row['labels'])
        with self.assertRaises(ValueError):
            encode(Tokenizer(), [{}, {}, {}], max_length=8)

    def test_epoch_visits_each_sample_once_and_keeps_tail(self):
        groups = epoch_groups(163, accumulation=8, seed=42)
        self.assertEqual(list(range(163)), sorted(sum(groups, [])))
        self.assertEqual(3, len(groups[-1]))
        self.assertEqual(groups, epoch_groups(163, accumulation=8, seed=42))
        self.assertNotEqual(groups, epoch_groups(163, accumulation=8, seed=43))

    def test_rejects_source_contamination_test_split_and_duplicate(self):
        row = {'messages': [{'role': r, 'content': 'x'} for r in ('system', 'user', 'assistant')],
               'metadata': {'teacher_source': 'rule_expert', 'model': None, 'split': 'train',
                            'prompt_sha256': 'x'}}
        validate_rows([row], 'train')
        with self.assertRaises(ValueError):
            validate_rows([row], 'test')
        with self.assertRaises(ValueError):
            validate_rows([row, row], 'train')
        row['metadata']['teacher_source'] = 'llm'
        with self.assertRaises(ValueError):
            validate_rows([row], 'train')


if __name__ == '__main__':
    unittest.main()
