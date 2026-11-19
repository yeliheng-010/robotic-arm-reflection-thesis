"""Export only LLM corrections immediately followed by accepted physical success."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reflection.reflector import Parameters
from training.qlora.data import make_messages


def verified_examples(result, result_path):
    records = result.get('records', [])
    history = []
    for index, record in enumerate(records):
        reflection = record.get('reflection')
        error = record.get('error')
        if not error or not reflection:
            continue
        if index + 1 < len(records):
            following = records[index + 1]
            if (reflection.get('source') == 'llm'
                    and following.get('accepted') is True
                    and following.get('physical_success') is True
                    and following.get('attempt') == record.get('attempt', -1) + 1):
                try:
                    current = Parameters().updated(record['parameters'])
                    expected = current.updated(reflection['changes'])
                    actual = Parameters().updated(following['parameters'])
                    if expected != actual:
                        raise ValueError('Executed parameters do not match correction')
                    cause = reflection['cause']
                    if not isinstance(cause, str) or not cause.strip():
                        raise ValueError('Empty diagnosis')
                except (KeyError, TypeError, ValueError):
                    pass
                else:
                    messages = make_messages(
                        result['instruction'], error, record['parameters'], history,
                        {'cause': cause, 'changes': reflection['changes']},
                    )
                    yield {
                        'messages': messages,
                        'metadata': {
                            'result_path': str(result_path),
                            'attempt': record['attempt'],
                            'verified_attempt': following['attempt'],
                            'source': result.get('source'),
                            'destination': result.get('destination'),
                            'seed': result.get('seed'),
                            'fault': result.get('fault'),
                            'perception': result.get('perception'),
                            'physical_success': True,
                            'accepted': True,
                            'teacher': 'llm',
                            'limitations': 'Immediate next-attempt success is selection evidence, not proof of causal benefit; images omitted.',
                        },
                    }
        history.append({'error': error, 'reflection': reflection})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.input.is_dir():
        parser.error('Input must be an existing run directory')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('Output directory must be empty')
    seen, examples = set(), []
    for path in sorted(args.input.rglob('result.json')):
        result = json.loads(path.read_text())
        for example in verified_examples(result, path.relative_to(args.input)):
            digest = hashlib.sha256(json.dumps(example['messages'], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            if digest in seen:
                continue
            seen.add(digest)
            example['metadata']['sample_sha256'] = digest
            example['metadata']['result_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            examples.append(example)
    if not examples:
        parser.error('No verified immediate-success LLM corrections found')
    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / 'train.jsonl'
    target.write_text(''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in examples))
    teacher = None
    manifest = args.input / 'manifest.json'
    if manifest.exists():
        teacher = json.loads(manifest.read_text()).get('preflight', {}).get('model_id')
    summary = {
        'input_run': str(args.input.resolve()), 'teacher_model': teacher,
        'sample_count': len(examples),
        'by_fault': dict(Counter(e['metadata']['fault'] for e in examples)),
        'dataset_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
        'split': 'smoke_only_unsplit',
        'purpose': 'Runtime validation only; no held-out effectiveness measurement',
        'format': 'text-reflection-v1',
    }
    (args.output / 'dataset_manifest.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
