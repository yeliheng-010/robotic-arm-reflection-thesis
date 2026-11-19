import unittest
import torch
from test_objective import RecordingModel, sample
from vt_objective import objective
from vf_update import update


class UpdateTests(unittest.TestCase):
    def test_token_weighting_matches_single_reference_gradient(self):
        model, reference = RecordingModel(), RecordingModel()
        first, second = sample(), sample()
        second['labels'][0, 3] = -100
        expected_loss = (2 * objective(reference, first) + objective(reference, second)) / 3
        expected_loss.backward()
        torch.nn.utils.clip_grad_norm_(reference.parameters(), 1.)
        expected = reference.scores.detach() - .01 * reference.scores.grad
        optimizer = torch.optim.SGD(model.parameters(), lr=.01)
        scaler = torch.amp.GradScaler('cuda', enabled=False)
        result = update(model, dict(model.named_parameters()), rows=[first, second],
            optimizer=optimizer, scaler=scaler, device='cpu')
        torch.testing.assert_close(expected, model.scores)
        self.assertEqual(3, result['supervised_tokens'])
        self.assertAlmostEqual(float(expected_loss.detach()), result['loss'], places=6)

    def test_invalid_supervision_does_not_update(self):
        model, row = RecordingModel(), sample()
        before = model.scores.detach().clone()
        row['labels'][:] = -100
        with self.assertRaises(AssertionError):
            update(model, dict(model.named_parameters()), rows=[row],
                optimizer=torch.optim.SGD(model.parameters(), lr=.01),
                scaler=torch.amp.GradScaler('cuda', enabled=False), device='cpu')
        torch.testing.assert_close(before, model.scores)


if __name__ == '__main__':
    unittest.main()
