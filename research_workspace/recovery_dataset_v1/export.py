import os
import json
from pathlib import Path
from collections import Counter
from f_common import read, save, sha
from collection_common import verify, split
from rc_gate import summarize, assess
from export_records import record, deduplicate, select_training

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'recovery_collection_v1'


def load():
    protocol = verify(SOURCE/'protocol.json')
    rows, stops, identities, batches = [], [], {}, []
    for path in sorted(SOURCE.glob('batches/*/physics/inventory.json')):
        inventory = verify(path)
        manifest = verify(path.parent/'manifest.json')
        for audit in (path.parent/'audits').glob('*.json'):
            assert verify(audit)['passed']
        assert inventory['summary'] == summarize(inventory['rows'])
        for row in inventory['rows']+inventory['stops']:
            assert row['split'] == split(row['seed']) == protocol['split_by_seed'][str(row['seed'])]
        rows.extend(inventory['rows'])
        stops.extend(inventory['stops'])
        identities[str(path)] = sha(path)
        batches.append(dict(batch=manifest['batch'], qualified=inventory['qualification_passed'],
            proposed=inventory['qualification_proposed']))
    assert batches, 'No fully audited collection batch'
    return rows, stops, identities, batches


def write_lines(path, rows):
    with path.open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    rows, stops, identities, batches = load()
    output = ROOT/'exports'/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    positive = [record(r) for r in rows if r['verified_recovery'] and r['eligible_natural']]
    candidates = deduplicate(positive+[record(r,stop=True) for r in stops])
    seed_sets = {s:{r['seed'] for r in candidates if r['split']==s} for s in ('train','dev')}
    assert not seed_sets['train'].intersection(seed_sets['dev'])
    counts = {}
    for target in ('train','dev'):
        values = select_training([r for r in candidates if r['split']==target])
        write_lines(output/(target+'.jsonl'), values)
        counts[target] = dict(records=len(values), actions=dict(Counter(r['action']['id'] for r in values)))
    write_lines(output/'outcomes.jsonl', rows)
    summary = summarize(rows)
    gate = assess(summary)
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md', SOURCE/'protocol.json']
    identities.update({str(p):sha(p) for p in paths})
    save(output/'manifest.json', dict(summary=summary, gate=gate, counts=counts, batches=batches,
        identities=identities, outputs={p.name:sha(p) for p in output.glob('*.jsonl')},
        training_ready=False, private_outcomes_not_model_input=True))
    print(dict(output=str(output), summary=summary, gate=gate, counts=counts), flush=True)


if __name__ == '__main__':
    main()
