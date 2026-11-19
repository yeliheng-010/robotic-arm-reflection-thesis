"""限定思考后由模型生成最终答案；只插入控制标记，不修补JSON。"""
import hashlib
import json
from stability.sampling_runtime import DECODING
from stability.teacher9_service import StrongTeacher
from stability.experiment import OUT

THOUGHT_TOKENS, ANSWER_TOKENS = 2048, 512
OUTPUT = OUT/'teacher9_budget_forced'


def finish_thought(raw, emit_final):
    closed = '</think>' in raw
    answer = raw.split('</think>', 1)[1].strip() if closed else ''
    if answer:
        return dict(text=answer, raw_answer='', answer_tokens=0,
                    forced_think_end=False, inserted_text='')
    inserted = '' if closed else '</think>\n\n'
    answer, tokens = emit_final(inserted)
    return dict(text=answer.strip(), raw_answer=answer, answer_tokens=tokens,
                forced_think_end=not closed, inserted_text=inserted)


class BudgetForcedTeacher(StrongTeacher):
    def __init__(self):
        super().__init__()
        self.thinking = True
        self.max_new_tokens = THOUGHT_TOKENS+ANSWER_TOKENS

    def identity(self):
        return dict(super().identity(), thinking=True, audit_log=str(OUTPUT/'requests.jsonl'),
            decoding={'thought': DECODING, 'answer': {'do_sample': False}},
            budget_control={'thought_tokens': THOUGHT_TOKENS, 'answer_tokens': ANSWER_TOKENS,
                            'method': 'insert_think_end_then_generate_actual_answer'},
            seed_policy='sha256_messages_first_8_hex')

    def emit_answer(self, generated, inserted):
        import torch
        ids = generated
        if inserted:
            suffix = self.tokenizer(inserted, add_special_tokens=False,
                                    return_tensors='pt').input_ids.to(generated.device)
            ids = torch.cat((generated, suffix), dim=1)
        output = self.model.generate(input_ids=ids, attention_mask=torch.ones_like(ids),
            max_new_tokens=ANSWER_TOKENS, do_sample=False,
            pad_token_id=self.tokenizer.eos_token_id)
        raw = self.tokenizer.decode(output[0, ids.shape[1]:], skip_special_tokens=True)
        return raw, int(output.shape[1]-ids.shape[1])

    def generate(self, messages):
        import torch
        seed = int(hashlib.sha256(json.dumps(messages, sort_keys=True,
            ensure_ascii=False).encode()).hexdigest()[:8], 16)
        torch.manual_seed(seed)
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=True, enable_thinking=True)
        inputs = self.tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
        count = inputs.input_ids.shape[1]
        if count > 4096:
            raise ValueError('Input exceeds the frozen token budget')
        with torch.inference_mode():
            first = self.model.generate(**inputs, max_new_tokens=THOUGHT_TOKENS,
                pad_token_id=self.tokenizer.eos_token_id, **DECODING)
            raw = self.tokenizer.decode(first[0, count:], skip_special_tokens=True)
            final = finish_thought(raw, lambda inserted: self.emit_answer(first, inserted))
        return dict(self.identity(), **final, raw_text=raw+final['raw_answer'], raw_thought=raw,
            input_tokens=int(count), first_stage_tokens=int(first.shape[1]-count),
            output_tokens=int(first.shape[1]-count)+final['answer_tokens'], seed=seed)
