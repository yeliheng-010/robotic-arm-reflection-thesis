"""从保存的像素重新核算；只在独立审计侧使用干净深度。"""
import numpy as np
from sd_common import read, sha
from diversity.noise import corrupt_depth
from diversity.runtime import digest
from sensor_math import surface


def frame(folder, config, *, index):
    audit, public = read(folder/'audit.json'), read(folder/'public.json')
    assert sha(folder/'private_sensor.npz') == audit['sensor_sha256']
    assert sha(folder/'rgb.png') == audit['rgb_sha256']
    with np.load(folder/'private_sensor.npz') as arrays:
        clean, noisy = arrays['clean'], arrays['noisy']
        assert digest(clean) == audit['clean_sha256'] and digest(noisy) == audit['noisy_sha256']
        assert audit['seed_components'] == [963800, config['seed'], 1, index]
        expected, stats = corrupt_depth(clean, config['sensor'],
                                       seed=np.random.SeedSequence(audit['seed_components']))
        np.testing.assert_array_equal(expected, noisy)
        assert stats == audit['stats']
        for name in ('source', 'destination'):
            actual = surface(noisy, arrays[name+'_mask'], transform=audit['transform'],
                             intrinsics=audit['intrinsics'])
            assert actual == public['observed'][name]
    assert audit['state_unchanged'] and public['observation_index'] == index
    if config['group'] == 'baseline':
        assert audit['clean_sha256'] == audit['noisy_sha256']
        assert stats['noise_rmse_m'] == 0 and stats['dropped_pixels'] == 0
    else:
        assert .0025 < stats['noise_rmse_m'] < .0035
        assert .015 < stats['dropout_fraction'] < .025
    return public, audit


def audit(folder, case, *, success):
    summary = read(folder/'observation_summary.json')
    count = 1 if success else 3
    paths = sorted((folder/'observations').glob('observation_*'))
    assert len(paths) == count and summary['additional_observations'] == count-1
    rows = [frame(p, case['config'], index=i) for i, p in enumerate(paths)]
    public, private = [r[0] for r in rows], [r[1] for r in rows]
    assert public == summary['public'] and private == summary['private']
    assert len({r['time_s'] for r in public}) == 1
    for name in ('state_sha256', 'clean_sha256', 'rgb_sha256'):
        assert len({r[name] for r in private}) == 1, name
    if case['item']['group'] == 'varied_noisy':
        assert len({r['noisy_sha256'] for r in private}) == count
    return dict(passed=True, frames=count, extra=count-1,
                private_audit_excluded=True, state_and_clean_frame_identical=True,
                noise=[r['stats'] for r in private])
