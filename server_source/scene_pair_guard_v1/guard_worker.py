"""单次安全回归；记录新增门控而不伪装成策略成功。"""
import os
import numpy as np
from sd_common import read, save, sha
from cp_worker import bound
from depth_runtime import context as depth_context
from candidate_runtime import context as candidate_context
from loopstudy import episode
from contact_capture import capture
from guard_runtime import context as guard_context
from guard_prepare import ROOT


def same_input(case, result):
    before = read(case['step']['result_path'])['records'][0]
    after = read(result['result_path'])['records'][0]
    for key in ('initial_qpos', 'initial_body_xyz', 'generated', 'returned'):
        np.testing.assert_array_equal(before['candidate_trace'][key], after['candidate_trace'][key])
    assert before['parameters'] == after['parameters']
    assert before['domain_randomization']['sensor_frames'][0] == after['domain_randomization']['sensor_frames'][0]
    return before, after


def run(case):
    folder = ROOT/'physics'/case['id']
    folder.mkdir(parents=True, exist_ok=False)
    item, config, trace = case['item'], case['config'], {}
    with capture(folder/'contacts.jsonl', item), bound(config), depth_context(), \
         candidate_context(config), guard_context(item, trace, contacts=case['strict_contacts']):
        result = episode.attempt(item, case['step']['state'], directory=folder/'attempt_1', index=1)
    before, after = same_input(case, result)
    save(folder/'guard.json', trace)
    save(folder/'audit.json', dict(same_inputs=True, old_success=before['physical_success'],
         success=after['physical_success'], step=result, trace_sha256=sha(folder/'contacts.jsonl'),
         guard_sha256=sha(folder/'guard.json')))
    print(case['id'], dict(success=result['success'], error=(after['error'] or {}).get('error_type'),
                          guard=trace), flush=True)


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    for case in manifest['cases']:
        run(case)
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    save(ROOT/'run_complete.json', dict(complete=True, attempts=len(manifest['cases']),
                                       manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
