"""检查新模型实例能恢复优化器、随机状态和样本位置。"""
import copy
import tempfile
import unittest
from pathlib import Path
import torch
from peft import LoraConfig, get_peft_model, get_peft_model_state_dict
from round2.checkpoint import save_bundle, restore_bundle


class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = torch.nn.Linear(4, 4)

    def forward(self, value):
        return self.linear(value)


def context():
    torch.manual_seed(42)
    model = get_peft_model(Toy(), LoraConfig(r=2, lora_alpha=4,
                          lora_dropout=.25, target_modules=['linear']))
    model.train()
    return dict(model=model, optimizer=torch.optim.AdamW(model.parameters(), lr=.01),
                scaler=torch.amp.GradScaler('cuda', enabled=False))


def step(ctx):
    ctx['optimizer'].zero_grad()
    loss = ctx['model'](torch.randn(3, 4)).square().mean()
    loss.backward()
    ctx['optimizer'].step()
    return loss.item()


class CheckpointTests(unittest.TestCase):
    def test_fresh_model_resume_matches_next_update(self):
        first = context()
        step(first)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'checkpoint'
            meta = dict(identity='frozen', step=1, order=[[1], [0]], updates=[{'step': 1}])
            save_bundle(first, path, meta)
            expected_loss = step(first)
            expected = copy.deepcopy(get_peft_model_state_dict(first['model']))
            resumed = context()
            actual = restore_bundle(resumed, path, 'frozen')
            self.assertEqual(meta, actual)
            self.assertEqual(expected_loss, step(resumed))
            for key, tensor in get_peft_model_state_dict(resumed['model']).items():
                self.assertTrue(torch.equal(expected[key], tensor), key)

    def test_rejects_wrong_identity_and_corrupt_checkpoint(self):
        ctx = context()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'checkpoint'
            save_bundle(ctx, path, dict(identity='frozen', step=0))
            with self.assertRaises(AssertionError):
                restore_bundle(context(), path, 'different')
            with (path/'training_state.pt').open('ab') as stream:
                stream.write(b'corrupt')
            with self.assertRaises(AssertionError):
                restore_bundle(context(), path, 'frozen')


if __name__ == '__main__':
    unittest.main()
