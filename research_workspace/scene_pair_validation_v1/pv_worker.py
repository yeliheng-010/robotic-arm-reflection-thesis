"""完整两场景验证；仅补充门控触发条件的原策略第三次。"""
from copy import deepcopy
import os
import sys
from unittest.mock import patch
from sd_common import read, save, sha
import pair_run
from pair_runtime import bound
from drop_recovery import enabled
from cm_runtime import attempt as original_attempt
from pv_protocol import ROOT, verify


def legacy(row, config, folder):
    steps = row['steps']
    branch = len(steps) == 3 and enabled(index=3, report=steps[1]['feedback'])
    if not branch:
        return dict(shared=True, success=row['success'], extra_attempts=0)
    with bound(config):
        step = original_attempt(row['item'], steps[2]['state'], directory=folder/'legacy_third',
                                policy='geometry', feedback=steps[1]['feedback'])
    a = read(steps[2]['result_path'])['records'][0]
    b = read(step['result_path'])['records'][0]
    for key in ('candidate_trace', 'domain_randomization', 'parameters'):
        assert a[key] == b[key], 'Unpaired third attempt: '+key
    assert not b['motion_extension']['active'] and a['motion_extension']['active']
    return dict(shared=False, success=step['success'], extra_attempts=1, step=step,
                same_initial_candidates_noise=True,
                sensor_audit=pair_run.execution_audits([step], config))


def main(index):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    task = manifest['items'][index]
    config = manifest['configs'][f"{task['seed']}_{task['group']}"]
    folder = ROOT/'physics'/task['id']
    def selected(seed, scene):
        assert (seed, scene) == (task['seed'], task['group'])
        return deepcopy(config)
    with patch.object(pair_run, 'configuration', selected):
        row = pair_run.run(task, folder)
    comparison = legacy(row, config, folder)
    save(folder/'comparison.json', dict(index=index, item=task, legacy=comparison,
         new_success=row['success'], result_sha256=sha(folder/'result.json'),
         manifest_sha256=sha(ROOT/'manifest.json')))
    print('PAIRED', task['id'], comparison['success'], row['success'], flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))
