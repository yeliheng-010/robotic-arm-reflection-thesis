"""修正审计源分类：运行日志可增长，源码/输入/数组仍逐份强校验。"""
from pathlib import Path
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.audit import check_state
from surface_grasp_v1.common import read, save, sha
from depth_diagnostic_v1.worker import ROOT, RUN
from depth_diagnostic_v1.numeric import samples, summary


def provenance(before):
    logs = {}
    for path, digest in before['inputs'].items():
        assert sha(path) == digest, path
    for name, digest in before['identities'].items():
        path = Path(name)
        current = sha(path)
        if path.parent == ROOT and path.name == 'run-6609.log':
            logs[name] = dict(start_sha256=digest, final_sha256=current, role='mutable_slurm_output')
        else:
            assert current == digest, name
    assert len(logs) == 1
    return logs


def recalculate(result):
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
    return rows


def main():
    logs = provenance(read(RUN / 'started.json'))
    result = read(RUN / 'result.json')
    assert sha(RUN / 'pixels.npz') == result['pixels_sha256']
    check_state(RUN)
    rows = recalculate(result)
    assert summary(rows) == result['original']
    save(RUN / 'audit_v2.json', dict(passed=True, independent_process=True,
        original_samples=len(rows), original=summary(rows), inputs_unchanged=True,
        mutable_logs=logs, corrected_source_sha256=sha(Path(__file__)),
        result_sha256=sha(RUN / 'result.json'), control_deployed=False))
    print(dict(passed=True, original=summary(rows), mutable_logs=logs), flush=True)


if __name__ == '__main__':
    main()
