"""每个资格条件都有接受/拒绝去向，仅接受者产生训练监督。"""
import os
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import PHYSICS, read, save, sha, verify
from rc_review import collect
from rc_gate import summarize, assess

ROOT = Path(__file__).resolve().parent


def disposition(case):
    name = case['item']['id']
    accepted = PHYSICS / 'audits' / (name+'.json')
    rejected = PHYSICS / 'audit_rejections' / (name+'.json')
    assert accepted.exists() != rejected.exists(), name
    path = accepted if accepted.exists() else rejected
    result = verify(path)
    assert result['passed'] is accepted.exists()
    assert result['manifest_sha256'] == sha(PHYSICS / 'manifest.json')
    consumed = read(PHYSICS / 'cases' / name / 'result.json')
    assert consumed['status'] == 'completed' and 1 <= consumed['attempts'] <= 7
    if accepted.exists():
        assert result['row']['attempts'] == consumed['attempts']
    else:
        assert result['reason'] == 'measured_robot_self_contact'
        assert result['consumed_attempts'] == consumed['attempts']
    return dict(id=name, accepted=accepted.exists(), attempts=consumed['attempts'], path=str(path))


def write_inventory(manifest, conditions):
    rows, stops = [], []
    accepted = {r['id'] for r in conditions if r['accepted']}
    for case in manifest['cases']:
        if case['item']['id'] in accepted:
            decisions, success = collect(case)
            rows.extend(decisions)
            stops.extend(success)
    summary = summarize(rows)
    paths = [PHYSICS / 'manifest.json', PHYSICS / 'complete_v2.json', ROOT / 'source_manifest.json']
    paths.extend(Path(r['path']) for r in conditions)
    assert not (PHYSICS / 'inventory.json').exists()
    save(PHYSICS / 'inventory.json', dict(summary=summary, gate=assess(summary), rows=rows, stops=stops,
        identities={str(p): sha(p) for p in paths}, qualification_proposed=len(manifest['qualification_rows']),
        qualification_passed=len(conditions), audit_accepted=len(accepted), audit_rejected=len(conditions)-len(accepted),
        exclusions=[r for r in conditions if not r['accepted']], model_calls=0,
        limitation='Audit rejected conditions preserved in full denominator but excluded from supervision'))
    print(dict(summary=summary, accepted=len(accepted), rejected=len(conditions)-len(accepted)), flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify(ROOT / 'source_manifest.json')
    manifest = verify(PHYSICS / 'manifest.json')
    conditions = [disposition(case) for case in manifest['cases']]
    attempts = sum(r['attempts'] for r in conditions)
    assert attempts <= manifest['max_attempts']
    assert not (PHYSICS / 'complete_v2.json').exists()
    save(PHYSICS / 'complete_v2.json', dict(all_conditions_accounted_for=True, conditions=conditions,
        attempts=attempts, model_calls=0, manifest_sha256=sha(PHYSICS / 'manifest.json'),
        all_conditions_safety_passed=all(r['accepted'] for r in conditions), training_ready=False))
    write_inventory(manifest, conditions)


if __name__ == '__main__':
    main()
