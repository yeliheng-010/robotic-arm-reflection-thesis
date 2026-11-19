"""只读定位真实入口与冻结观测不同的首个数据层。"""
import json
from pathlib import Path
import numpy as np

PARENT = Path(__file__).resolve().parents[2]
OLD = PARENT/'qualification_strategy_v1/actual/cases/F0_964345_varied_noisy'
NEW = PARENT/'joint_representation_v1/trial/preflight'


def compare(a,b):
    if a.shape != b.shape:
        return dict(equal=False,shapes=[list(a.shape),list(b.shape)])
    same = np.array_equal(a,b,equal_nan=True)
    result = dict(equal=same,shape=list(a.shape),dtypes=[str(a.dtype),str(b.dtype)])
    if not same:
        delta = np.abs(a.astype(float)-b.astype(float))
        finite = delta[np.isfinite(delta)]
        result.update(different=int(np.count_nonzero(a!=b)),max_delta=float(finite.max()) if finite.size else None)
    return result


def main():
    rows = {}
    for name in ('span_inputs.npz','execution/attempt_1/depth_evidence.npz'):
        with np.load(OLD/name) as a,np.load(NEW/name) as b:
            assert set(a.files) == set(b.files)
            rows[name] = {key:compare(a[key],b[key]) for key in a.files}
    path = Path(__file__).with_name('result.json')
    with path.open('x') as stream:
        json.dump(rows,stream,indent=2,allow_nan=False)
    print(rows,flush=True)


if __name__ == '__main__':
    main()
