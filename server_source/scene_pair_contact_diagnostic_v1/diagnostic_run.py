"""固定六个分支，仅增加采样，核验原始场景和候选未变。"""
import os
from pathlib import Path
import numpy as np
from sd_common import read, save, sha
from cp_common import verify as source_verify
from cp_worker import bound
from depth_runtime import context as depth_context
from candidate_runtime import context as candidate_context
from loopstudy import episode
import sd_physics
from contact_capture import capture

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'scene_pair_candidates_v1'
SELECTED = (('961103_varied_noisy_0', 1), ('961112_varied_noisy_0', 1),
            ('961108_varied_noisy_1', 3), ('961104_varied_noisy_0', 1),
            ('961103_baseline_0', 1), ('961107_varied_noisy_0', 1))


def prepare():
    previous = source_verify()
    ledger = read(SOURCE/'paired_ledger.json')
    cases = []
    for task_id, index in SELECTED:
        row = next(r for r in ledger if r['item']['id'] == task_id)
        step = row['new']['steps'][index-1]
        cases.append(dict(item=row['item'], config=previous['configs'][task_id], step=step,
                          feedback=row['new']['steps'][index-2]['feedback'] if index > 1 else None))
    identities = dict(previous['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')})
    identities.update({str(SOURCE/n): sha(SOURCE/n) for n in ('manifest.json', 'paired_ledger.json')})
    save(ROOT/'manifest.json', dict(cases=cases, identities=identities, diagnostic_only=True))


def unchanged(case, new):
    old = read(case['step']['result_path'])['records'][0]
    current = read(new['result_path'])['records'][0]
    for key in ('parameters', 'physical_success', 'accepted', 'executor_state'):
        assert old[key] == current[key], key
    for key in ('initial_qpos', 'initial_body_xyz', 'generated', 'returned'):
        np.testing.assert_array_equal(old['candidate_trace'][key], current['candidate_trace'][key])
    assert old['domain_randomization'] == current['domain_randomization']
    for key in ('position', 'placement_residual_xy', 'xy_error_m', 'tilt_deg'):
        np.testing.assert_array_equal(old['evaluation'][key], current['evaluation'][key])
    assert (old['error'] or {}).get('error_type') == (current['error'] or {}).get('error_type')
    assert old.get('execution_adapter') == current.get('execution_adapter')
    return dict(passed=True, exact_arrays=True, identical_sensor=True, identical_outcome=True)


def execute(case):
    item, config, step = case['item'], case['config'], case['step']
    folder = ROOT/'physics'/item['id']
    folder.mkdir(parents=True, exist_ok=False)
    with capture(folder/'contacts.jsonl', item), bound(config), depth_context(), candidate_context(config):
        if step['index'] == 3:
            result = sd_physics.motion_attempt(item, step['state'], directory=folder/'attempt_3',
                       policy='geometry', feedback=case['feedback'])
        else:
            result = episode.attempt(item, step['state'], directory=folder/'attempt_1', index=1)
    audit = unchanged(case, result)
    save(folder/'audit.json', dict(**audit, step=result, trace_sha256=sha(folder/'contacts.jsonl')))
    print(item['id'], result['success'], audit, flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    assert not (ROOT/'manifest.json').exists()
    prepare()
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    for case in manifest['cases']:
        execute(case)
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    save(ROOT/'verification.json', dict(passed=True, attempts=6, diagnostic_only=True,
                                       manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
