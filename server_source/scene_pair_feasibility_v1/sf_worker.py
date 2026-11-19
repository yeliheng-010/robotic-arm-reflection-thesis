"""只回放相机变更后的增强场景，原配置引用冻结控制结果。"""
from copy import deepcopy
import os
import sys
from unittest.mock import patch
from sd_common import save, sha
import pair_run
from sf_common import ROOT, verify, enhanced


def main(index):
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    task = enhanced(manifest)[index]
    config = manifest['configs'][f"{task['seed']}_{task['group']}"]
    folder = ROOT/'physics'/task['id']
    if not config['camera_accepted']:
        save(folder/'result.json', dict(item=task, qualified=False, success=False, steps=[], decisions=[],
             status='camera_configuration_rejected', model_calls=0, training_approved=False, test_used=False))
    else:
        def selected(seed, scene):
            assert (seed, scene) == (task['seed'], task['group'])
            return deepcopy(config)
        with patch.object(pair_run, 'configuration', selected):
            pair_run.run(task, folder)
    save(folder/'identity.json', dict(item=task, manifest_sha256=sha(ROOT/'manifest.json'),
                                    result_sha256=sha(folder/'result.json')))
    print('ACCOUNTED', task['id'], flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))
