"""独立重算真实观测，适配逻辑尝试编号与共享首帧。"""
from pathlib import Path
import numpy as np
from diversity.noise import corrupt_depth
from diversity.runtime import digest
from sensor_math import surface
from nc_common import read, sha


def frame(path, config, *, attempt, index):
    folder = Path(path)
    audit, public = read(folder/'audit.json'), read(folder/'public.json')
    assert sha(folder/'private_sensor.npz') == audit['sensor_sha256']
    assert sha(folder/'rgb.png') == audit['rgb_sha256']
    assert audit['seed_components'] == [963800, config['seed'], attempt, index]
    with np.load(folder/'private_sensor.npz') as arrays:
        clean, noisy = arrays['clean'], arrays['noisy']
        assert digest(clean) == audit['clean_sha256'] and digest(noisy) == audit['noisy_sha256']
        expected, stats = corrupt_depth(clean, config['sensor'], seed=np.random.SeedSequence(audit['seed_components']))
        np.testing.assert_array_equal(expected, noisy)
        assert stats == audit['stats']
        for name in ('source', 'destination'):
            value = surface(noisy, arrays[name+'_mask'], transform=audit['transform'], intrinsics=audit['intrinsics'])
            assert value == public['observed'][name]
    assert public['attempt'] == attempt and public['observation_index'] == index and audit['state_unchanged']
    if config['group'] == 'baseline':
        assert stats['noise_rmse_m'] == 0 and stats['dropped_pixels'] == 0
    else:
        assert .0025 < stats['noise_rmse_m'] < .0035 and .015 < stats['dropout_fraction'] < .025
    return public, audit


def view(reference, case):
    assert sha(reference['path']) == reference['sha256']
    summary = read(reference['path'])
    attempt = summary['public'][0]['attempt']
    rows = [frame(path, case['config'], attempt=attempt, index=i) for i, path in enumerate(summary['paths'])]
    assert [r[0] for r in rows] == summary['public'] and [r[1] for r in rows] == summary['private']
    assert len({r[0]['time_s'] for r in rows}) == 1
    for key in ('state_sha256', 'clean_sha256'):
        assert len({r[1][key] for r in rows}) == 1
    if case['item']['group'] == 'varied_noisy':
        assert len({r[1]['noisy_sha256'] for r in rows}) == len(rows)
    return summary
