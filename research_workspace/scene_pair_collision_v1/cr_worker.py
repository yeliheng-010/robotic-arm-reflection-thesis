"""共享前两次，仅执行反馈触发的第三次姿态分支。"""
import os
from copy import deepcopy
from sd_common import read, save, sha
from pair_runtime import bound
from depth_runtime import context as depth_context
from collision_runtime import context
from drop_recovery import attempt
from cr_common import ROOT, SOURCE, verify


def main():
    assert os.environ.get('SLURM_JOB_ID'), 'Use Slurm'
    manifest = verify()
    ledger = read(SOURCE/'paired_ledger.json')
    for row in ledger:
        item, old = row['item'], row['new']
        if item['id'] not in manifest['selected']:
            continue
        folder = ROOT/'physics'/item['id']
        folder.mkdir(parents=True, exist_ok=False)
        feedback = old['steps'][1]['feedback']
        with bound(manifest['configs'][item['id']]), depth_context(), context(feedback):
            step = attempt(item, old['steps'][2]['state'], directory=folder/'attempt_3',
                           policy='geometry', feedback=feedback)
        new = deepcopy(old)
        new.update(steps=[*old['steps'][:2], step], success=step['success'])
        save(folder/'result.json', new)
        save(folder/'identity.json', dict(item=item, manifest_sha256=sha(ROOT/'manifest.json'),
             result_sha256=sha(folder/'result.json'), shared_prefix=2, actual_attempts=1))
        print(item['id'], step['success'], flush=True)


if __name__ == '__main__':
    main()
