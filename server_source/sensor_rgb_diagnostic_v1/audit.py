import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.audit import check_state
from surface_grasp_v1.common import read, save, sha
from sensor_rgb_diagnostic_v1.worker import RUN, comparisons


def main():
    before = read(RUN / 'started.json')
    for path, digest in dict(before['inputs'], **before['identities']).items():
        assert sha(path) == digest, path
    result = read(RUN / 'result.json')
    checks = {}
    for seed, row in result.items():
        folder = RUN / seed
        check_state(folder)
        assert sha(folder / 'rgb.npz') == row['arrays_sha256']
        with np.load(folder / 'rgb.npz') as data:
            assert comparisons({key: data[key] for key in data.files}) == row['comparisons']
        checks[seed] = all(v['passed'] for v in row['comparisons']['adjacent'].values())
    save(RUN / 'audit.json', dict(passed=True, rgb_checks=checks, independent_process=True,
        inputs_unchanged=True, result_sha256=sha(RUN / 'result.json')))
    print(dict(passed=True, rgb_checks=checks), flush=True)


if __name__ == '__main__':
    main()
