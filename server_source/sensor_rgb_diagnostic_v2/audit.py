import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.audit import check_state
from surface_grasp_v1.common import read, save, sha
from sensor_rgb_diagnostic_v2.worker import RUN, SOURCE, SEED, selected, comparisons, archived_comparisons


def main():
    before = read(RUN / 'started.json')
    for path, digest in dict(before['inputs'], **before['identities']).items():
        assert sha(path) == digest, path
    assert selected(read(SOURCE / str(SEED) / 'observations.json')) == before['indices']
    result = read(RUN / 'result.json')
    assert list(result) == [str(i) for i in before['indices']]
    for index, row in result.items():
        folder = RUN / index
        check_state(folder)
        assert sha(folder / 'rgb.npz') == row['arrays_sha256']
        assert row['actual_samples'] == dict(rgb=4, original_depth=4, original_segmentation=4,
                                            no_msaa_depth=0, no_msaa_segmentation=0)
        with np.load(folder / 'rgb.npz') as data:
            values = {key: data[key] for key in data.files}
            assert comparisons(values) == row['comparisons']
            with np.load(SOURCE / str(SEED) / f'rgb_{index}.npz') as archived:
                assert archived_comparisons(values, archived) == row['archived_comparisons']
    save(RUN / 'audit.json', dict(passed=True, independent_process=True, inputs_unchanged=True,
        result_sha256=sha(RUN / 'result.json'), indices=before['indices'], task_motion_attempts=0,
        model_calls=0, training_runs=0))
    print(dict(passed=True, indices=before['indices']), flush=True)


if __name__ == '__main__':
    main()
