import unittest
from types import SimpleNamespace
import torch
from vt_objective import boundary, objective


def sample():
    return dict(input_ids=torch.tensor([[1, 2, 3, 4, 5]]),
        attention_mask=torch.ones(1, 5, dtype=torch.long),
        labels=torch.tensor([[-100, -100, -100, 4, 5]]),
        pixel_values=torch.ones(2, 4), image_grid_thw=torch.tensor([[1, 1, 1], [1, 1, 1]]))


class RecordingModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.scores = torch.nn.Parameter(torch.arange(35, dtype=torch.float).reshape(1, 5, 7) / 10)
        self.seen = None

    def forward(self, **kwargs):
        self.seen = kwargs
        return SimpleNamespace(logits=self.scores[:, -kwargs['logits_to_keep']:, :])


class ObjectiveTests(unittest.TestCase):
    def test_matches_full_causal_loss_and_gradients(self):
        model, values = RecordingModel(), sample()
        measured = objective(model, values)
        reference = torch.nn.functional.cross_entropy(model.scores[:, :-1].reshape(-1, 7),
            values['labels'][:, 1:].reshape(-1), ignore_index=-100)
        torch.testing.assert_close(reference, measured)
        measured.backward()
        self.assertTrue(torch.isfinite(model.scores.grad).all())
        self.assertGreater(float(model.scores.grad.abs().sum()), 0)
        self.assertEqual(0, int(torch.count_nonzero(model.scores.grad[:, :2])))

    def test_images_and_complete_context_reach_model(self):
        model, values = RecordingModel(), sample()
        objective(model, values)
        for key in ('input_ids', 'pixel_values', 'image_grid_thw'):
            self.assertIs(values[key], model.seen[key])
        self.assertNotIn('labels', model.seen)
        self.assertFalse(model.seen['use_cache'])

    def test_missing_images_rejected(self):
        values = sample()
        del values['pixel_values']
        with self.assertRaises(AssertionError):
            boundary(values)

    def test_wrong_or_noncontiguous_labels_rejected(self):
        for labels in ([-100, -100, 3, -100, 5], [-100, -100, -100, 6, 5], [-100] * 5):
            values = sample()
            values['labels'] = torch.tensor([labels])
            with self.assertRaises(AssertionError):
                boundary(values)


if __name__ == '__main__':
    unittest.main()
