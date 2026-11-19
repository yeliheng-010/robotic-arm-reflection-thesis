"""独立文本生成入口；旧冻结服务和128-token常量保持不变。"""
import time
import torch
import runtime
from f_common import PARENT, sha
from f_response import MAX_TOKENS, MAX_INPUT_TOKENS, SEED, finish


class Generator:
    def __init__(self):
        assert runtime.__file__.endswith('/candidate_sft_v2/runtime.py'), runtime.__file__
        config = runtime.verify_manifest()
        assert config['seed'] == SEED
        self.model, _, self.tokenizer, self.environment = runtime.setup(config)
        self.model.eval()
        self.identity = dict(base='Qwen3.5-4B', adapter_enabled=False,
                             runtime_manifest_sha256=sha(PARENT/'candidate_sft_v2/manifest.json'),
                             model_path=config['model'])

    def prepare(self, messages):
        assert [r['role'] for r in messages] == ['system', 'user']
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False,
                    add_generation_prompt=True, enable_thinking=False)
        values = self.tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
        assert values['input_ids'].shape[1] <= MAX_INPUT_TOKENS, 'Reject long input without truncation'
        return values

    def generate(self, values):
        torch.manual_seed(SEED)
        length = values['input_ids'].shape[1]
        started = time.monotonic()
        with self.model.disable_adapter(), torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            output = self.model.generate(**values, max_new_tokens=MAX_TOKENS, do_sample=False,
                     use_cache=True, logits_to_keep=1, pad_token_id=self.tokenizer.pad_token_id)
        tokens = output[0, length:].tolist()
        eos = self.model.generation_config.eos_token_id
        reason = finish(tokens, eos)
        return dict(text=self.tokenizer.decode(tokens, skip_special_tokens=True), finish_reason=reason,
                    prompt_tokens=length, completion_tokens=len(tokens), generated_ids=tokens,
                    eos_ids=eos, elapsed_s=time.monotonic()-started, identity=self.identity)
