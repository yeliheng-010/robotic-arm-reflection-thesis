"""仅用六个训练任务比较提示词和证据，不查看验证/测试任务。"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT.parent
TRAIN_IDS = (16, 24, 32, 136, 144, 152)


def assess(response, first):
    from reflection.reflector import Parameters
    from training.refine.prompt import parse_response
    try:
        parsed = parse_response(response['text'], Parameters().updated(first['parameters']))
        return dict(valid=True, reflection=parsed.to_dict())
    except (ValueError, TypeError) as error:
        return dict(valid=False, error=str(error))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--architecture', choices=['qwen25', 'qwen35'], default='qwen25')
    parser.add_argument('--output', default='development_v4')
    parser.add_argument('--thinking', action='store_true')
    parser.add_argument('--diagnostics-only', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    from training.refine.prompt import build_messages
    from training.refine.runtime import FrozenModel
    from training.refine.instrumentation import diagnostic_snapshot
    from types import SimpleNamespace
    model = FrozenModel(args.architecture, thinking=args.thinking)
    records = []
    for index in TRAIN_IDS:
        path = OUT / 'parity' / f'{index:05d}' / 'result.json'
        result = json.loads(path.read_text())
        first = result['records'][0]
        for variant in ('original_evidence', 'normalized_diagnostics'):
            if (args.thinking or args.diagnostics_only) and variant == 'original_evidence':
                continue
            report = json.loads(json.dumps(first['error']))
            if variant == 'original_evidence':
                report['evidence'].pop('diagnostics', None)
            else:
                state = dict(report['evidence']['diagnostics'])
                if state.get('motion_segment') == 'return_home':
                    state.pop('commanded_tcp_xyz', None)
                report['evidence']['diagnostics'] = diagnostic_snapshot(
                    state, SimpleNamespace(stage=report['stage']))
            messages = build_messages(result['instruction'], report, parameters=first['parameters'])
            response = model.generate(messages)
            row = dict(case=f'{index:05d}', variant=variant, messages=messages,
                       response=response, assessment=assess(response, first))
            records.append(row)
            (OUT / f'{args.output}_{args.architecture}.json').write_text(json.dumps(records, ensure_ascii=False, indent=2))
            print(json.dumps({k: row[k] for k in ('case', 'variant', 'assessment')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
