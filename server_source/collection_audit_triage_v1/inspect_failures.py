"""只读重放审计失败，记录误差与真实自接触；不放宽断言、不执行物理。"""
import os
import traceback
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import goal_audit_geometry_v2 as geometry
import sv_strategy_audit
from audit_v5 import audit_attempt
from collection_common import PHYSICS, BRANCHES, read, save, sha, verify
from sr_audit import measured
from self_geometry import forbidden

ROOT = Path(__file__).resolve().parent
NAMES = ('R0_964160_varied_noisy', 'R0_964143_varied_noisy')


def contacts(folder):
    import json
    hits = []
    for line in (folder / 'contacts.jsonl').read_text().splitlines():
        sample = json.loads(line)
        for contact in sample['contacts']:
            if forbidden(contact['roots'], contact['distance']):
                hits.append(dict(action=sample['action'], event=sample['event'], contact=contact))
    result = measured(folder)
    result.pop('closing_end')
    result.update(hit_count=len(hits), first_hits=hits[:8],
        minimum_distance=min((h['contact']['distance'] for h in hits), default=None))
    return result


def inspect_step(case, step):
    evidence = {}
    original = geometry.reconstructed_placement

    def probe(row, current):
        center = np.array(row['target']) + np.array(current['source_center']) - np.array(row['pose'])[:3, 3]
        gap = float(center[2] - current['source_half'][2] - current['wall_top'])
        evidence.update(reconstructed=current, selected=row,
            rebuilt_gap=gap, stored_gap=row['goal']['bottom_gap'],
            gap_difference=gap-row['goal']['bottom_gap'])
        return original(row, current)

    try:
        with patch.object(geometry, 'reconstructed_placement', probe), \
             patch.object(sv_strategy_audit, 'audit_attempt', audit_attempt):
            checked = sv_strategy_audit.inspect(case, step)
        evidence['original_audit_passed'] = True
    except Exception as error:
        evidence.update(original_audit_passed=False, error=repr(error), traceback=traceback.format_exc())
    folder = Path(step['session_path'])
    trace = read(folder / 'route.json')
    evidence.update(step=step, contact=contacts(folder), cached_geometry=trace.get('endpoints', {}).get('geometry'))
    return evidence


def main():
    assert os.environ.get('SLURM_JOB_ID') and PHYSICS.parent.name == '004'
    manifest = verify(PHYSICS / 'manifest.json')
    result = {}
    for name in NAMES:
        case = next(c for c in manifest['cases'] if c['item']['id'] == name)
        folder = PHYSICS / 'cases' / name
        steps = {}
        for branch in BRANCHES:
            for step in read(folder / branch / 'result.json')['ledger']['steps']:
                steps[step['session_path']] = step
        result[name] = [inspect_step(case, step) for step in steps.values()]
    save(ROOT / 'results' / ('job_'+os.environ['SLURM_JOB_ID']+'.json'), dict(cases=result,
        physical_attempts=0, model_calls=0, training_updates=0,
        identities={str(PHYSICS / 'manifest.json'): sha(PHYSICS / 'manifest.json')}))
    for name, values in result.items():
        print(name, [dict(path=v['step']['session_path'], passed=v['original_audit_passed'],
            gap_delta=v.get('gap_difference'), contact=v['contact']) for v in values], flush=True)


if __name__ == '__main__':
    main()
