"""通过可观测假模型验证生成时不关闭adapter；不冒充真实模型验证。"""
import unittest
from types import SimpleNamespace
from contextlib import nullcontext
from unittest.mock import patch
import torch
from ac_generator import AdapterGenerator
from f_response import MAX_TOKENS


class FakeModel:
    active_adapters = ['trained']
    generation_config = SimpleNamespace(eos_token_id=9)

    def disable_adapter(self):
        raise AssertionError('Adapter must remain enabled')

    def generate(self, **kwargs):
        assert kwargs['max_new_tokens'] == MAX_TOKENS
        assert kwargs['do_sample'] is False
        return torch.tensor([[1, 2, 3, 9]])


class GeneratorTests(unittest.TestCase):
    def generator(self):
        value = AdapterGenerator.__new__(AdapterGenerator)
        value.model = FakeModel()
        value.identity = dict(adapter_enabled=True)
        value.tokenizer = SimpleNamespace(pad_token_id=0,
            decode=lambda tokens, **kwargs: 'response')
        return value

    @patch('ac_generator.torch.autocast', return_value=nullcontext())
    def test_adapter_enabled_and_original_budget(self, autocast):
        value = self.generator().generate(dict(input_ids=torch.tensor([[1, 2]])))
        self.assertEqual('stop', value['finish_reason'])
        self.assertEqual([3, 9], value['generated_ids'])
        self.assertTrue(value['identity']['adapter_enabled'])

    def test_wrong_active_adapter_rejected_before_generation(self):
        value = self.generator()
        value.model.active_adapters = ['default']
        with self.assertRaises(AssertionError):
            value.generate(dict(input_ids=torch.tensor([[1, 2]])))


if __name__ == '__main__':
    unittest.main()
