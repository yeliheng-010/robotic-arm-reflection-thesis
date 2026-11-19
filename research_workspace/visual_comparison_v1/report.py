import os
import re
from collections import Counter
from pathlib import Path
from collection_common import read, save, sha, verify
from vc_metrics import classify
from sv_strategy_actions import validate, choose
from prepare import lines

ROOT = Path(__file__).resolve().parent


def main():
    assert os.environ.get('SLURM_JOB_ID')
    export_job = os.environ['RECOVERY_EXPORT_JOB']
    assert re.fullmatch(r'\d+', export_job)
    prepared = ROOT/'prepared'/('export_'+export_job)
    verify(prepared/'manifest.json')
    complete = read(prepared/'base_comparison/complete.json')
    assert complete['passed'] and complete['manifest_sha256'] == sha(prepared/'manifest.json')
    private = {r['input_id']: r for r in lines(prepared/'private_outcomes.jsonl')}
    inputs = {r['input_id']: r for r in lines(prepared/'inputs.jsonl')}
    assert len(complete['rows']) == len(private)
    rows = []
    for item in complete['rows']:
        facts = private[item['input_id']]
        path = prepared/'base_comparison'/item['input_id']/'response.json'
        assert sha(path) == item['response_sha256']
        request = inputs[item['input_id']]['request']
        assert validate(read(path), request, mode='direct') == item['validation']
        assert choose(request) == item['fixed_rule_action']
        valid = item['validation']['valid']
        model_action = item['validation']['parsed']['action'] if valid else None
        rows.append(dict(input_id=item['input_id'], snapshot_id=facts['snapshot_id'],
            completed=facts['completed'], model=classify(model_action, facts['outcomes'],
                valid=valid, completed=facts['completed']),
            fixed_rule=classify(item['fixed_rule_action'], facts['outcomes'], valid=True,
                completed=facts['completed'])))
    summary = {method: dict(Counter(r[method] for r in rows)) for method in ('model', 'fixed_rule')}
    save(prepared/'report.json', dict(summary=summary, rows=rows, inputs=len(rows),
        natural_snapshots=len({r['snapshot_id'] for r in rows if not r['completed']}),
        model_calls=complete['model_calls'], physical_attempts=0, training_updates=0,
        identities={str(prepared/'manifest.json'): sha(prepared/'manifest.json'),
            str(prepared/'base_comparison/complete.json'): sha(prepared/'base_comparison/complete.json')},
        limitation='Offline observed-option comparison; unmeasured choices are unknown, not failures'))
    print(summary, flush=True)


if __name__ == '__main__':
    main()
