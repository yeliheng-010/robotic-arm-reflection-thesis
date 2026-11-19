"""资格实验：同一已验证执行器，最多三次尝试，不调用模型。"""
import os
import sys
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
from sd_config import ROOT, MOVING
from sd_common import verify, save, sha, read, config_for
from sd_runtime import context
from controlled.config import scenario
from loopstudy import episode
from loopstudy.actions import initial
from rc_policy import decide
from cm_runtime import attempt as motion_attempt
from sd_render import probe


@contextmanager
def bound(config):
    with context(config), patch.object(episode, 'configuration', lambda item: scenario(item['seed'], 'clean')):
        yield


def execute(item, folder):
    steps, decisions, state = [], [], initial()
    for index in range(1, 4):
        directory = folder/f'attempt_{index}'
        if index == 3:
            step = motion_attempt(item, state, directory=directory, policy='geometry', feedback=steps[-1]['feedback'])
        else:
            step = episode.attempt(item, state, directory=directory, index=index)
        steps.append(step)
        if step['success'] or index == 3:
            break
        decision = decide(steps, decisions, method='rule')
        decisions.append(decision)
        if decision['selected'] is None:
            break
        state = decision['selected']['state']
    return steps, decisions


def check_initial(steps, config, static):
    records = [read(step['result_path'])['records'][0] for step in steps]
    first = records[0]['candidate_trace']
    for name in MOVING:
        np.testing.assert_allclose(static['body_positions'][name],
            first['initial_body_xyz'][static['body_ids'][name]], atol=1e-8, rtol=0)
    for record in records[1:]:
        trace = record['candidate_trace']
        np.testing.assert_allclose(first['initial_qpos'], trace['initial_qpos'], atol=1e-8, rtol=0)
        np.testing.assert_allclose(first['initial_body_xyz'], trace['initial_body_xyz'], atol=1e-8, rtol=0)
    return dict(same_initial_state=True, attempts=len(records), camera=config['camera'],
                appearance=config['appearance'])


def run(index):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    item = manifest['items'][index]
    config = config_for(item, manifest)
    folder = ROOT/'physics'/item['id']
    folder.mkdir(parents=True, exist_ok=False)
    static = probe(config, folder/'qualification')
    source, destination = (static['visibility'][item[key]]['qualified'] for key in ('source', 'destination'))
    qualified = (source and destination and static['calibration']['passed']
                 and config['geometry_accepted'] and config['compiled_check']['passed'])
    row = dict(index=index, item=item, qualified=qualified, status='qualification_rejected',
               steps=[], decisions=[], success=False, model_calls=0, test_used=False)
    if qualified:
        with bound(config):
            steps, decisions = execute(item, folder)
        row.update(status='executed', steps=steps, decisions=decisions, success=steps[-1]['success'],
                   initial_audit=check_initial(steps, config, static))
    row['manifest_sha256'] = sha(ROOT/'manifest.json')
    save(folder/'result.json', row)
    print(item['id'], row['status'], row['success'], flush=True)


if __name__ == '__main__':
    run(int(sys.argv[1]))
