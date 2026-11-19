import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.audit import check_state
from surface_grasp_v1.common import read, save, sha
from depth_diagnostic_v1.sampling import RUN, OUTPUT, metrics


def main():
    for path, digest in read(OUTPUT / 'started.json')['inputs'].items():
        assert sha(path) == digest, path
    check_state(OUTPUT)
    result, reference = read(OUTPUT / 'result.json'), read(RUN / 'result.json')
    with np.load(RUN / 'pixels.npz') as data:
        old_depth, old_roots = data['depth'], data['roots']
    for label, row in result['variants'].items():
        assert sha(OUTPUT / f'{label}.npz') == row['arrays_sha256']
        with np.load(OUTPUT / f'{label}.npz') as data:
            assert metrics(data['depth'], old_roots, reference) == row['fixed_old_mask']
            assert metrics(data['depth'], data['roots'], reference) == row['native_mask']
            assert bool(np.array_equal(data['depth'], old_depth)) == row['same_depth_as_archived']
            assert bool(np.array_equal(data['roots'], old_roots)) == row['same_roots_as_archived']
    save(OUTPUT / 'audit.json', dict(passed=True, independent_process=True,
        inputs_unchanged=True, result_sha256=sha(OUTPUT / 'result.json'), control_deployed=False))
    print(dict(passed=True), flush=True)


if __name__ == '__main__':
    main()
