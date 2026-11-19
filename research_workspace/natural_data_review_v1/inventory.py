"""只读已审计来源，私有去重与训练候选分开。"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    return hashlib.sha256(raw.encode()).hexdigest()


def identity(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def snapshot(branch, event):
    step = branch['ledger']['steps'][event['after_attempt']-1]
    assert not step['success']
    summaries = [read(ref['path']) for ref in branch['views']]
    initial = next(row for row in summaries if row['public'][0]['attempt'] == step['index'])
    private = initial['private'][0]
    task = {k: branch['ledger']['item'][k] for k in ('source', 'destination')}
    return digest(dict(task=task, state=private['state_sha256'], clean=private['clean_sha256']))


def decisions(branch, case):
    rows = []
    for event in branch['decisions']:
        bundle = read(event['input_path'])
        action = event.get('action')
        executes = action is not None and action['id'] not in ('STOP', 'OBSERVE')
        following = branch['ledger']['steps'][event['after_attempt']] if executes else None
        rows.append(dict(snapshot_id=snapshot(branch, event), condition=case['item']['id'],
            seed=case['item']['seed'], split=case['item']['split'], method=branch['method'],
            input_path=event['input_path'], input_sha256=identity(event['input_path']),
            input_content_sha256=digest(bundle['request']), status=event['status'], action=action,
            next_execution=following, direct_recovery=bool(following and following['success']),
            supervision_claim='executed_successor_only_not_optimal_or_causal',
            private_dedup_fields_excluded_from_model=True))
    return rows


def collect(source):
    manifest, complete = read(source/'manifest.json'), read(source/'complete.json')
    assert complete['passed']
    for seed in manifest['seeds']:
        audit = read(source/f'audit_{seed}.json')
        assert audit['passed'] and audit['manifest_sha256'] == identity(source/'manifest.json')
        assert all(identity(p) == h for p, h in audit['identities'].items())
    rows, success_initial = [], []
    for case in manifest['cases']:
        folder = source/'cases'/case['item']['id']
        result = read(folder/'result.json')
        if result['status'] != 'completed':
            continue
        first = read(folder/'first/step.json')
        if first['success']:
            success_initial.append(dict(condition=case['item']['id'], step=first))
        for method in result['methods']:
            rows.extend(decisions(read(folder/method/'result.json'), case))
    return rows, success_initial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    rows, initial = collect(args.source)
    recovered = [r for r in rows if r['direct_recovery']]
    summary = dict(decisions=len(rows), unique_failure_snapshots=len({r['snapshot_id'] for r in rows}),
        direct_recoveries=len({(r['snapshot_id'], digest(r['action'])) for r in recovered}),
        recovery_action_types=sorted({r['action']['id'] for r in recovered}),
        correction_action_types=sorted({r['action']['id'] for r in recovered if r['action']['id'] != 'RETRY'}),
        seeds=sorted({r['seed'] for r in rows}), first_success_conditions=len(initial),
        training_ready=False, pilot_is_training_data=False)
    value = dict(summary=summary, rows=rows, initial_successes=initial,
        source=str(args.source), manifest_sha256=identity(args.source/'manifest.json'))
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
