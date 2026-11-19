"""仅961112单因素诊断；不加入策略、不修改正式成功率。"""
import os
from copy import deepcopy
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
from sd_common import read, save, sha
from cp_worker import bound
from depth_runtime import context as depth_context
from candidate_runtime import context as candidate_context
from loopstudy import episode
from contact_capture import capture
from diagnostic_run import ROOT

SLOW_LIFT_SECONDS = 3.0
INSERTION_DELTA_M = -.008
VARIANTS = ('slower_lift', 'deeper_grasp')


@contextmanager
def intervention(variant):
    original = grasp.GraspFlow.move_to_point
    def move(flow, *args, **kwargs):
        if variant == 'slower_lift':
            assert kwargs['time4'] == 1.0
            kwargs['time4'] = SLOW_LIFT_SECONDS
        return original(flow, *args, **kwargs)
    with patch.object(grasp.GraspFlow, 'move_to_point', move):
        yield


def audit(case, result, *, variant, folder):
    before = read(case['step']['result_path'])['records'][0]
    after = read(result['result_path'])['records'][0]
    for key in ('initial_qpos', 'initial_body_xyz', 'generated', 'returned'):
        np.testing.assert_array_equal(before['candidate_trace'][key], after['candidate_trace'][key])
    assert before['domain_randomization']['sensor_frames'][0] == after['domain_randomization']['sensor_frames'][0]
    expected = deepcopy(before['parameters'])
    if variant == 'deeper_grasp':
        expected['grasp_offset'][2] = INSERTION_DELTA_M
    assert expected == after['parameters']
    if variant == 'slower_lift':
        assert after['execution_adapter']['durations'] == [0.0, 3.0, 1.0, 1.0]
        original = read_trace(ROOT/'physics'/case['item']['id']/'contacts.jsonl')
        current = read_trace(folder/'contacts.jsonl')
        assert [r for r in original if r['time'] <= 6] == [r for r in current if r['time'] <= 6]
    return dict(passed=True, observation_and_candidates_unchanged=True, single_factor=variant)


def read_trace(path):
    import json
    return [json.loads(line) for line in path.read_text().splitlines()]


def run_case(case, variant):
    folder = ROOT/'contrasts'/variant
    folder.mkdir(parents=True, exist_ok=False)
    state = deepcopy(case['step']['state'])
    if variant == 'deeper_grasp':
        state['parameters']['grasp_offset'][2] = INSERTION_DELTA_M
    config, item = case['config'], case['item']
    with capture(folder/'contacts.jsonl', item), intervention(variant), bound(config), \
         depth_context(), candidate_context(config):
        result = episode.attempt(item, state, directory=folder/'attempt_1', index=1)
    verification = audit(case, result, variant=variant, folder=folder)
    save(folder/'audit.json', dict(**verification, step=result, trace_sha256=sha(folder/'contacts.jsonl')))
    print(variant, result['success'], result['feedback'], flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest
    case = next(c for c in manifest['cases'] if c['item']['id'] == '961112_varied_noisy_0')
    protocol = dict(case=case, variants=VARIANTS, lift_seconds=SLOW_LIFT_SECONDS,
                    insertion_delta_m=INSERTION_DELTA_M, diagnostic_only=True,
                    identities={str(p): sha(p) for p in ROOT.glob('*.py')})
    save(ROOT/'contrast_manifest.json', protocol)
    for variant in VARIANTS:
        run_case(case, variant)
    for path, digest in protocol['identities'].items():
        assert sha(path) == digest
    save(ROOT/'contrast_verification.json', dict(passed=True, attempts=2, diagnostic_only=True,
                                               manifest_sha256=sha(ROOT/'contrast_manifest.json')))


if __name__ == '__main__':
    main()
