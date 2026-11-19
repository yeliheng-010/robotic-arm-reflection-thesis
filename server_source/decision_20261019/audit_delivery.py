"""实验包外的只读交付核验；不参与候选选择或物理执行。"""
from collections import Counter
import json
from pathlib import Path
import numpy as np

from decision.experiment import BASE, COLLECTION, OUT
from decision.develop import TRAIN_IDS
from training.refine.validate import verify_pair
from training.refine.validate import fingerprint as base_fingerprint
from decision.verify import first_signature


def read(path):
    return json.loads(path.read_text())


def audit_provenance(directory, server):
    count = 0
    for path in directory.glob('*/hybrid/choices.jsonl'):
        events = [json.loads(line) for line in path.read_text().splitlines()]
        for event in events:
            if 'response' not in event:
                continue
            assert any(s.get('request', {}).get('messages') == event['messages']
                       and s.get('response') == event['response'] for s in server)
            count += 1
    return count


def arm_statistics(directory, arm):
    results = [read(p) for p in directory.glob('*/' + arm + '/result.json')]
    errors = [r['reflection_error'] for t in results for r in t['records'] if 'reflection_error' in r]
    refused = sum(e == 'Abstained or unknown candidate: abstain' for e in errors)
    return {'tasks': len(results), 'success': sum(t['success'] for t in results),
            'first_success': sum(t['records'][0]['accepted'] for t in results),
            'recoveries': sum(t['success'] and not t['records'][0]['accepted'] for t in results),
            'first_errors': dict(Counter((t['records'][0]['error'] or {}).get('error_type') for t in results)),
            'attempts': sum(t['attempts'] for t in results), 'abstentions': refused,
            'other_reflection_errors': len(errors) - refused}


def historical_comparison():
    checks = []
    for index, original_id in enumerate(TRAIN_IDS):
        old = read(COLLECTION / 'tasks' / f'{original_id:05d}/result.json')
        actual = read(OUT / 'train_v1' / f'{index:02d}/hybrid/result.json')
        assert first_signature(old) == first_signature(actual)
        delta = np.asarray(old['records'][0]['evaluation']['position']) - actual['records'][0]['evaluation']['position']
        exact = True
        try:
            verify_pair(old, actual)
        except AssertionError:
            exact = False
        checks.append({'case': original_id, 'matches_at_1e_8': exact,
                       'max_position_difference_m': float(np.max(np.abs(delta)))})
    return checks


def main():
    assert read(BASE / 'validation_final/manifest.json')['code_sha256'] == base_fingerprint()
    server = [json.loads(line) for line in (OUT / 'teacher/requests.jsonl').read_text().splitlines()]
    checks = historical_comparison()
    output = {'training_initial_physics_matches_original': sum(x['matches_at_1e_8'] for x in checks),
              'historical_comparison': checks, 'previous_experiment_code_unchanged': True}
    for run in ('train_v1', 'holdout_v1'):
        directory = OUT / run
        manifest = read(directory / 'manifest.json')
        output[run] = {'server_matched_hybrid_answers': audit_provenance(directory, server),
                       'statistics': {arm: arm_statistics(directory, arm) for arm in manifest['arms']}}
    output['note'] = 'Abstention is a retained failure, separate from malformed output; no pure-LLM export'
    (OUT / 'delivery_audit.json').write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

