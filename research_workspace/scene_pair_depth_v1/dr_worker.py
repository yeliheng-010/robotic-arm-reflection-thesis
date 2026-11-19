"""只执行离线门禁证明会触发恢复的任务。"""
import os
from copy import deepcopy
from unittest.mock import patch
from sd_common import save, sha
import pair_run
from depth_runtime import context
from dr_common import ROOT, verify


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    for item in manifest['items']:
        if item['id'] not in manifest['selected']:
            continue
        config = manifest['configs'][item['id']]
        folder = ROOT/'physics'/item['id']
        with patch.object(pair_run, 'configuration', lambda seed, scene: deepcopy(config)), context():
            pair_run.run(item, folder)
        save(folder/'identity.json', dict(item=item, result_sha256=sha(folder/'result.json'),
             manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
