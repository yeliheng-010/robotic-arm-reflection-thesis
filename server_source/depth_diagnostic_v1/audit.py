import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.audit import check_state
from surface_grasp_v1.common import read, save, sha
from depth_diagnostic_v1.worker import RUN
from depth_diagnostic_v1.numeric import samples, summary


def main():
    before = read(RUN / 'started.json')
    for path, digest in dict(before['inputs'], **before['identities']).items():
        assert sha(path) == digest
    result = read(RUN / 'result.json')
    assert sha(RUN / 'pixels.npz') == result['pixels_sha256']
    check_state(RUN)
    rows = []
    with np.load(RUN / 'pixels.npz') as data:
        for name, record in result['records'].items():
            for kernel in (3, 5, 7):
                values = samples(data['depth'], data['roots'] == result['body_ids'][name],
                    transform=np.asarray(result['transform']), intrinsics=result['intrinsics'],
                    box=result['boxes'][name], kernel=kernel)
                if kernel == 3:
                    for value in values:
                        value.update(name=name, inside_isolated=bool(data[name][value['v'], value['u']]))
                    rows.extend(values)
                assert values == record['variants'][str(kernel)]
    assert summary(rows) == result['original']
    save(RUN / 'audit.json', dict(passed=True, independent_process=True,
        original_samples=len(rows), original=summary(rows), inputs_unchanged=True,
        result_sha256=sha(RUN / 'result.json'), control_deployed=False))
    print(dict(passed=True, original=summary(rows)), flush=True)


if __name__ == '__main__':
    main()
