"""离线检查真实报告的教师输入预算，不调用模型、不改变证据。"""
import json
from pathlib import Path
from transformers import AutoTokenizer
from stability.prompt import build_messages


def main():
    root = Path('/home/yeliheng/grasp_server/stability_20261019')
    tokenizer = AutoTokenizer.from_pretrained('/home/yeliheng/grasp_server/qwen35/models/Qwen3.5-4B',
                                             local_files_only=True)
    rows = []
    for path in sorted((root/'train_v3').glob('*/stable/result.json')):
        result = json.loads(path.read_text())
        history = []
        for record in result['records']:
            if record['error'] is None:
                continue
            messages = build_messages(result['instruction'], record['error'],
                                      parameters=record['parameters'], history=history)
            text = tokenizer.apply_chat_template(messages, tokenize=False,
                add_generation_prompt=True, enable_thinking=False)
            tokens = tokenizer(text, add_special_tokens=False)['input_ids']
            rows.append(dict(case=path.parent.parent.name, attempt=record['attempt'], tokens=len(tokens)))
            if 'reflection' in record:
                history.append(dict(error=record['error'], reflection=record['reflection']))
    (root/'prompt-sizes-compact.json').write_text(json.dumps(rows, indent=2))
    print(json.dumps(rows))


if __name__ == '__main__':
    main()

