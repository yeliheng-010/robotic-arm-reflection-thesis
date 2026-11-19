"""选择契约：模型不能编造参数，混合来源不能变为纯LLM。"""
import json
import unittest

from reflection.reflector import Reflection
from decision.selector import parse_choice


class SelectorTests(unittest.TestCase):
    def setUp(self):
        self.choices = [{'id': 'align_release', 'changes': {'place_offset': [.18, 0, 0]}}]

    def test_choice_preserves_numeric_candidate_and_hybrid_source(self):
        answer = parse_choice('{"cause":"final residual","choice":"align_release"}', self.choices)
        self.assertIsInstance(answer, Reflection)
        self.assertEqual('hybrid_llm_selector', answer.source)
        self.assertEqual(self.choices[0]['changes'], answer.changes)

    def test_model_cannot_override_candidate_numbers(self):
        with self.assertRaises(ValueError):
            parse_choice('{"cause":"x","choice":"align_release","changes":{"place_offset":[-.18,0,0]}}', self.choices)

    def test_fabricated_choice_and_abstention_have_no_fallback(self):
        for name in ('invented', 'abstain'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                parse_choice(json.dumps({'cause': 'x', 'choice': name}), self.choices)

    def test_duplicate_key_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_choice('{"cause":"x","choice":"invented","choice":"align_release"}', self.choices)


if __name__ == '__main__':
    unittest.main()
