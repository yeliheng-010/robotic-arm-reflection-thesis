"""只读取训练输入，保留真实选择结果。"""
import argparse
import json
from pathlib import Path

from reflection.reflector import Parameters
from decision.selector import build_request, generate, parse_choice

BASE = Path('/home/yeliheng/grasp_server/improvement_20261019')
OUT = Path(__file__).resolve().parents[1]
TRAIN_IDS = (16, 24, 32, 136, 144, 152)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', default='http://127.0.0.1:18822')
    args = parser.parse_args()
    rows = []
    for index in TRAIN_IDS:
        task = json.loads((BASE / 'parity_v4' / f'{index:05d}/result.json').read_text())
        first = task['records'][0]
        parameters = Parameters().updated(first['parameters'])
        messages, choices = build_request(task['instruction'], first['error'],
            parameters=parameters, source=task['source'])
        response = generate(messages, args.endpoint)
        row = {'case': f'{index:05d}', 'messages': messages, 'candidates': choices, 'response': response}
        try:
            row['compiled'] = parse_choice(response['text'], choices).to_dict()
        except ValueError as error:
            row['error'] = str(error)
        rows.append(row)
        (OUT / 'development.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
        print(json.dumps({k: v for k, v in row.items() if k in ('case', 'compiled', 'error')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
