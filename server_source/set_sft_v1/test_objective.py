"""输入等权、多成功均分与严格集合评估的边界。"""
import copy
import unittest
import torch
from types import SimpleNamespace
from objective import weighted_variants, score_text
from loss import suffix_loss


def row(answer):
    ids = [1, 2, 3]+answer
    return dict(input_ids=ids, attention_mask=[1]*len(ids), labels=[-100]*3+answer)


class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = torch.nn.Embedding(11, 11)

    def forward(self, input_ids, attention_mask, logits_to_keep):
        return SimpleNamespace(logits=self.layer(input_ids)[:, -logits_to_keep:])


class ObjectiveTests(unittest.TestCase):
    def test_each_input_equal_despite_answer_count_and_length(self):
        groups = [dict(variants=[row([4])]), dict(variants=[row([5, 6]), row([7, 8, 9])])]
        self.assertEqual([.5, .25, .25], [w for _, w in weighted_variants(groups)])

    def test_streamed_gradient_equals_nested_mean(self):
        torch.manual_seed(42)
        first = Tiny()
        second = copy.deepcopy(first)
        groups = [dict(variants=[row([4])]), dict(variants=[row([5, 6]), row([7, 8, 9])])]
        expected = torch.stack([torch.stack([suffix_loss(first, r, device='cpu')
                                for r in g['variants']]).mean() for g in groups]).mean()
        expected.backward()
        measured = 0.
        for value, weight in weighted_variants(groups):
            loss = suffix_loss(second, value, device='cpu')*weight
            measured += float(loss.detach())
            loss.backward()
        torch.testing.assert_close(expected.detach(), torch.tensor(measured))
        for a, b in zip(first.parameters(), second.parameters()):
            torch.testing.assert_close(a.grad, b.grad)

    def test_singleton_reduces_to_original_per_sample_loss(self):
        sample = row([4, 5])
        self.assertEqual([(sample, 1.)], list(weighted_variants([dict(variants=[sample])])))

    def test_empty_group_rejected(self):
        with self.assertRaises(ValueError):
            list(weighted_variants([dict(variants=[])]))

    def test_epoch_covers_189_inputs_with_tail_five(self):
        from stability.sft_data import epoch_groups
        order = epoch_groups(189, accumulation=8, seed=42)
        self.assertEqual(24, len(order))
        self.assertEqual(5, len(order[-1]))
        self.assertEqual(list(range(189)), sorted(i for group in order for i in group))

    def test_alternate_success_accepted(self):
        result = score_text('{"action_id":"b"}', candidates=['a', 'b', 'c'], accepted=['a', 'b'])
        self.assertTrue(result['candidate_valid'] and result['set_match'])

    def test_legal_unverified_action_separate_from_invalid(self):
        result = score_text('{"action_id":"c"}', candidates=['a', 'b', 'c'], accepted=['a', 'b'])
        self.assertTrue(result['candidate_valid'])
        self.assertFalse(result['set_match'])

    def test_duplicate_key_extra_fields_and_unknown_rejected(self):
        texts = ['{"action_id":"a","action_id":"b"}', '{"action_id":"a","reason":"x"}',
                 '{"action_id":"unknown"}', '```json\n{"action_id":"a"}\n```']
        for text in texts:
            self.assertFalse(score_text(text, candidates=['a', 'b'], accepted=['a'])['candidate_valid'])


if __name__ == '__main__':
    unittest.main()
