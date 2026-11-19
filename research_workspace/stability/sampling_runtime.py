"""冻结解码配置与按输入派生的种子，避免贪心思考陷入重复循环。"""
import hashlib
import json
from training.refine.runtime import FrozenModel, final_answer

DECODING = {'do_sample': True, 'temperature': .6, 'top_p': .95,
            'top_k': 20, 'repetition_penalty': 1.1}


class SamplingModel(FrozenModel):
    def __init__(self):
        super().__init__('qwen35', thinking=True)
        self.max_new_tokens = 4096

    def identity(self):
        return dict(model=self.path, architecture=self.architecture, adapter=None, frozen=True,
                    thinking=True, max_new_tokens=self.max_new_tokens, decoding=DECODING,
                    seed_policy='sha256_messages_first_8_hex')

    def generate(self, messages):
        import torch
        seed = int(hashlib.sha256(json.dumps(messages, sort_keys=True,
                       ensure_ascii=False).encode()).hexdigest()[:8], 16)
        torch.manual_seed(seed)
        text = self.tokenizer.apply_chat_template(messages, tokenize=False,
                        add_generation_prompt=True, enable_thinking=True)
        inputs = self.tokenizer(text, add_special_tokens=False, return_tensors='pt').to('cuda')
        count = inputs.input_ids.shape[1]
        if count > 4096:
            raise ValueError('Input exceeds the frozen token budget')
        with torch.inference_mode():
            output = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens,
                        pad_token_id=self.tokenizer.eos_token_id, **DECODING)
        raw = self.tokenizer.decode(output[0, count:], skip_special_tokens=True)
        try:
            answer = final_answer(raw, thinking=True)
        except ValueError:
            answer = ''
        return dict(self.identity(), text=answer, raw_text=raw, input_tokens=int(count),
                    output_tokens=int(output.shape[1]-count), seed=seed)
