"""固定相机/观测预算，组合已单独验证的局部过程并记录新后果。"""
import os
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch
from sd_common import save, sha
import pair_run
import sd_physics
from depth_runtime import context as depth_context
from collision_runtime import context as collision_context
from candidate_runtime import context as candidate_context
from cp_common import ROOT, verify

PREVIOUS_BOUND = pair_run.bound


@contextmanager
def bound(config):
    with PREVIOUS_BOUND(config):
        original = sd_physics.motion_attempt
        def attempt(item, state, *, directory, policy, feedback):
            with collision_context(feedback):
                return original(item, state, directory=directory, policy=policy, feedback=feedback)
        with patch.object(sd_physics, 'motion_attempt', attempt):
            yield


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    for item in manifest['items']:
        if item['id'] not in manifest['selected']:
            continue
        config = manifest['configs'][item['id']]
        folder = ROOT/'physics'/item['id']
        with patch.object(pair_run, 'configuration', lambda seed, scene: deepcopy(config)), \
             patch.object(pair_run, 'bound', bound), depth_context(), candidate_context(config):
            pair_run.run(item, folder)
        save(folder/'identity.json', dict(item=item, result_sha256=sha(folder/'result.json'),
             manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
