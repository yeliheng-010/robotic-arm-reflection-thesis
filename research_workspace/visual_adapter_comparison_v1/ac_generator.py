"""显式启用已验证的正式adapter，避免沿用基础生成器的disable_adapter。"""
import time
import torch
from ac_common import common, TRAINING
from mm_generator import VisualGenerator
from f_response import MAX_TOKENS, SEED, finish


class AdapterGenerator(VisualGenerator):
    def __init__(self):
        settings = common.config()
        assert settings['seed'] == SEED
        self.model, _, self.tokenizer, self.environment = common.runtime.setup(
            settings, adapter=TRAINING / 'training' / 'adapter')
        self.model.eval()
        self.processor = common.processor(settings)
        self.identity = dict(base='Qwen3.5-4B', adapter_enabled=True,
            model_path=settings['model'], manifest_sha256=common.sha(TRAINING / 'manifest.json'),
            training_result_sha256=common.sha(TRAINING / 'training' / 'result.json'))

    def generate(self, values):
        assert self.model.active_adapters == ['trained']
        assert self.identity['adapter_enabled'] is True
        torch.manual_seed(SEED)
        length = values['input_ids'].shape[1]
        started = time.monotonic()
        with torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            output = self.model.generate(**values, max_new_tokens=MAX_TOKENS, do_sample=False,
                use_cache=True, logits_to_keep=1, pad_token_id=self.tokenizer.pad_token_id)
        tokens = output[0, length:].tolist()
        eos = self.model.generation_config.eos_token_id
        return dict(text=self.tokenizer.decode(tokens, skip_special_tokens=True),
            finish_reason=finish(tokens, eos), prompt_tokens=length, completion_tokens=len(tokens),
            generated_ids=tokens, eos_ids=eos, elapsed_s=time.monotonic()-started, identity=self.identity)
