"""相机按布局选择，任务资格共享，两个策略始终独立存储。"""
import sys
from copy import deepcopy
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import cc_qualify
from cv_select import select
from cv_entry import approved_config
from fa_common import RUN, POLICIES, read, save, sha, verify, base, case_at


def camera(seed):
    cases = verify(RUN/'manifest.json')['cases']
    case = next(c for c in cases if c['item']['seed'] == seed and c['item']['group'] == 'varied_noisy')
    config = case['config']
    if not config['geometry_accepted'] or not config['compiled_check']['passed']:
        result = dict(accepted=False, status='layout_geometry_rejected')
    else:
        _, result = select(config, RUN/'cameras'/str(seed))
    save(RUN/'camera_results'/(str(seed)+'.json'), result)
    print(dict(seed=seed, camera_accepted=result['accepted']), flush=True)


def prepare(original):
    name, seed = original['item']['id'], original['item']['seed']
    config = approved_config(RUN/'cameras'/str(seed), original['config'])
    registry = verify(RUN/'manifest.json')
    identities = dict(registry['identities'])
    paths = [RUN/'manifest.json', RUN/'cameras'/str(seed)/'selection.json',
             RUN/'cameras'/str(seed)/'accepted_config.json']
    identities.update({str(p): sha(p) for p in paths})
    for policy in POLICIES:
        case = deepcopy(original)
        case['config'] = deepcopy(config)
        case['strategy'] = 'observed_top' if policy == 'improved' else 'original'
        save(base(name, policy)/'manifest.json', dict(cases=[case], identities=identities,
            policy=policy, attempts_per_case=1, max_model_calls=0, training_updates=0))


def qualify(name):
    folder = base(name, 'original')
    case = case_at(folder)
    with patch.object(cc_qualify, 'PILOT', folder):
        cc_qualify.qualify(case)
    path = folder/'qualification'/str(case['item']['seed'])/'result.json'
    other = base(name, 'improved')
    row = read(path)
    row.update(source_path=str(path), source_sha256=sha(path), manifest_sha256=sha(other/'manifest.json'))
    save(other/'qualification'/str(case['item']['seed'])/'result.json', row)


if __name__ == '__main__':
    mode, value = sys.argv[1:]
    if mode == 'camera':
        camera(int(value))
    elif mode == 'qualify':
        qualify(value)
    else:
        raise ValueError(mode)
