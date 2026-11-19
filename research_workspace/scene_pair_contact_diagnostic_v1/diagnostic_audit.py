"""独立重读原始结果及采样；诊断不改全量实验分母。"""
import os
import math
from sd_common import read, save, sha
from diagnostic_run import ROOT, unchanged
from contrast_run import read_trace, audit
from analyze_contacts import action_stats, witness, bilateral


def ignored_contacts(rows, item):
    matches = []
    for row in rows:
        selected = [c for c in row['contacts'] if 'ur5e_base' in c['roots']
                    and item['destination'] in c['roots'] and c['force'][0] > 0]
        if selected:
            matches.append(dict(time=row['time'], action=row['action'],
                                normal_force=sum(c['force'][0] for c in selected), contacts=selected))
    return dict(samples=len(matches), first=matches[0] if matches else None,
                peak=max(matches, key=lambda r: r['normal_force']) if matches else None)


def validate_trace(rows):
    assert rows and rows[0]['event'] == 'begin' and rows[-1]['event'] == 'end_or_abort'
    assert all(b['time'] >= a['time'] for a, b in zip(rows, rows[1:]))
    assert all(math.isfinite(v) for row in rows for v in row['source'])
    assert all(row['action'] != 'idle' for row in rows)


def statistics(rows, item):
    rows = [dict(row, line=index+1) for index, row in enumerate(rows)]
    validate_trace(rows)
    carry = [r for r in rows if r['action'] == 'move_to_point']
    source = item['source']
    lost = next((r for r in carry if not bilateral(r, source)), None)
    return dict(samples=len(rows), actions=action_stats(rows, source),
                first_loss=witness(lost, source) if lost else None,
                max_lift_above_initial_m=max([r['source'][2] for r in carry] or [rows[0]['source'][2]])
                                        - rows[0]['source'][2],
                arm_destination_contacts=ignored_contacts(rows, item))


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest, contrast = read(ROOT/'manifest.json'), read(ROOT/'contrast_manifest.json')
    identities = dict(manifest['identities'], **contrast['identities'])
    for path, digest in identities.items():
        assert sha(path) == digest, path
    rows, files = [], {}
    for case in manifest['cases']:
        folder = ROOT/'physics'/case['item']['id']
        evidence = read(folder/'audit.json')
        unchanged(case, evidence['step'])
        assert sha(folder/'contacts.jsonl') == evidence['trace_sha256']
        assert sha(evidence['step']['result_path']) == evidence['step']['result_sha256']
        files[str(folder/'contacts.jsonl')] = evidence['trace_sha256']
        rows.append(dict(id=case['item']['id'], **statistics(read_trace(folder/'contacts.jsonl'), case['item'])))
    trials = []
    for variant in contrast['variants']:
        folder = ROOT/'contrasts'/variant
        evidence = read(folder/'audit.json')
        audit(contrast['case'], evidence['step'], variant=variant, folder=folder)
        assert sha(folder/'contacts.jsonl') == evidence['trace_sha256']
        assert sha(evidence['step']['result_path']) == evidence['step']['result_sha256']
        files[str(folder/'contacts.jsonl')] = evidence['trace_sha256']
        trials.append(dict(variant=variant, step=evidence['step'],
                           **statistics(read_trace(folder/'contacts.jsonl'), contrast['case']['item'])))
    save(ROOT/'diagnosis.json', dict(cases=rows, contrasts=trials))
    save(ROOT/'final_audit.json', dict(passed=True, replay_attempts=6, contrast_attempts=2,
         diagnostic_only=True, promotion_allowed=False, identities_checked=len(identities),
         traces=files, manifest_sha256=sha(ROOT/'manifest.json'),
         contrast_sha256=sha(ROOT/'contrast_manifest.json'), diagnosis_sha256=sha(ROOT/'diagnosis.json')))
    print(dict(passed=True, replay_attempts=6, contrast_attempts=2), flush=True)


if __name__ == '__main__':
    main()
