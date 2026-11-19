"""独立进程复算实际物理结果，另核对成对初态输入。"""
import sys
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from rh_audit import inspect
from fa_common import base, case_at, read, save, sha


def audit(name, policy):
    folder = base(name, policy)
    case = case_at(folder)
    result_path = folder/'cases'/str(case['item']['seed'])/'result.json'
    assert read(result_path)['manifest_sha256'] == sha(folder/'manifest.json')
    result = inspect(case, base=folder)
    paths = [p for p in (folder/'cases').rglob('*') if p.is_file()]
    result.update(identities={str(p): sha(p) for p in paths}, manifest_sha256=sha(folder/'manifest.json'))
    save(folder/'audit.json', result)
    print(dict(id=name, policy=policy, passed=result['passed'], success=result.get('success')), flush=True)


def pair(name):
    folders = [base(name, p) for p in ('original', 'improved')]
    cases = [case_at(f) for f in folders]
    assert cases[0]['strategy'] == 'original' and cases[1]['strategy'] == 'observed_top'
    assert {k:v for k,v in cases[0].items() if k != 'strategy'} == {
        k:v for k,v in cases[1].items() if k != 'strategy'}
    seed = str(cases[0]['item']['seed'])
    paths = [f/'cases'/seed/'first/span_inputs.npz' for f in folders]
    with np.load(paths[0]) as first, np.load(paths[1]) as second:
        assert set(first.files) == set(second.files)
        assert {'camera_points', 'world_points', 'depth', 'mask'} <= set(first.files)
        for key in first.files:
            np.testing.assert_array_equal(first[key], second[key])
        keys = first.files
    save(folders[0].parent/'pair.json', dict(passed=True, identical_arrays=keys,
        identities={str(p): sha(p) for p in paths}, strategy_only_case_difference=True))


if __name__ == '__main__':
    if sys.argv[1] == 'pair':
        pair(sys.argv[2])
    else:
        audit(*sys.argv[1:])
