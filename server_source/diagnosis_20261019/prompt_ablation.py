"""固定六个训练输入，只切换旧/新提示词；不执行物理任务或生成训练集。"""
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path('/home/yeliheng/grasp_server/overnight_20261019/code')
OUT = Path('/home/yeliheng/grasp_server/diagnosis_20261019')
MODEL = '/home/yeliheng/grasp_qlora/models/Qwen2.5-7B-Instruct'
CASE_IDS = (16, 24, 32, 136, 144, 152)


def load_model():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    assert torch.cuda.device_count() == 1
    torch.set_num_threads(4)
    torch.backends.cuda.enable_flash_sdp(False)
    tokenizer = AutoTokenizer.from_pretrained(MODEL, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL, local_files_only=True, torch_dtype=torch.float16,
        device_map={'': 0}, attn_implementation='sdpa',
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
    model.eval()
    return tokenizer, model


def generate(pair, messages):
    import torch
    tokenizer, model = pair
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
    assert inputs.input_ids.shape[1] <= 4096
    with torch.inference_mode():
        output = model.generate(**inputs, max_new_tokens=256, do_sample=False,
                                pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(output[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)


def validate(raw, parameters):
    from reflection.reflector import Parameters
    try:
        content = raw.strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        answer = json.loads(content)
        assert isinstance(answer.get('cause'), str) and answer['cause'].strip()
        Parameters().updated(parameters).updated(answer.get('changes'))
        return dict(valid=True, answer=answer)
    except (AssertionError, ValueError, TypeError, KeyError) as error:
        return dict(valid=False, error=str(error))


def main():
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from training.qlora.data import SYSTEM as OLD_SYSTEM, make_messages
    from training.overnight.prompt import SYSTEM as NEW_SYSTEM
    plan = json.loads((ROOT.parent / 'collection/plan.json').read_text())
    pair = load_model()
    records = []
    for index in CASE_IDS:
        assert plan[index]['split'] == 'train'
        path = ROOT.parent / 'collection/tasks' / f'{index:05d}' / 'result.json'
        result = json.loads(path.read_text())
        first = result['records'][0]
        for version, system in [('v1', OLD_SYSTEM), ('v2', NEW_SYSTEM)]:
            messages = make_messages(result['instruction'], first['error'], first['parameters'], [], {})[:-1]
            messages[0]['content'] = system
            raw = generate(pair, messages)
            record = dict(case=f'{index:05d}', version=version, messages=messages,
                          raw=raw, validation=validate(raw, first['parameters']),
                          result_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            records.append(record)
            (OUT / 'prompt_ablation.json').write_text(json.dumps(dict(model=MODEL,
                adapter=None, do_sample=False, max_new_tokens=256, records=records),
                ensure_ascii=False, indent=2))
            print(json.dumps({k: record[k] for k in ('case', 'version', 'validation')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

