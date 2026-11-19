"""预算控制不能编造或修补最终模型答案。"""
import unittest
from unittest.mock import Mock
from stability.budget_forcing import finish_thought, BudgetForcedTeacher


class BudgetTests(unittest.TestCase):
    def test_natural_final_is_preserved_without_another_generation(self):
        emit = Mock()
        result = finish_thought('analysis</think>\n{"changes":{}}', emit)
        self.assertEqual('{"changes":{}}', result['text'])
        emit.assert_not_called()
        self.assertEqual('', result['inserted_text'])

    def test_exhausted_budget_uses_actual_second_generation_unrepaired(self):
        emit = Mock(return_value=('invalid model output', 3))
        result = finish_thought('unfinished analysis', emit)
        emit.assert_called_once_with('</think>\n\n')
        self.assertEqual('invalid model output', result['text'])
        self.assertTrue(result['forced_think_end'])
        self.assertEqual(3, result['answer_tokens'])

    def test_closed_thought_without_answer_does_not_insert_another_marker(self):
        emit = Mock(return_value=('{}', 1))
        result = finish_thought('analysis</think>', emit)
        emit.assert_called_once_with('')
        self.assertFalse(result['forced_think_end'])

    def test_empty_suffix_preserves_integer_token_ids(self):
        import torch
        model = BudgetForcedTeacher.__new__(BudgetForcedTeacher)
        model.tokenizer = Mock(eos_token_id=0)
        model.tokenizer.decode.return_value = '{}'
        model.model = Mock()
        model.model.generate.return_value = torch.tensor([[1, 2, 3]])
        raw, count = model.emit_answer(torch.tensor([[1, 2]]), '')
        supplied = model.model.generate.call_args.kwargs['input_ids']
        self.assertEqual(torch.int64, supplied.dtype)
        model.tokenizer.assert_not_called()
        self.assertEqual(('{}', 1), (raw, count))


if __name__ == '__main__':
    unittest.main()

