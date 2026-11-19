"""记录冻结拟合器内部求解轨迹，不修改旧源码或使用真值选解。"""
import hashlib
import json
import platform
from pathlib import Path
from unittest.mock import patch

import numpy as np
import scipy
from scipy.optimize import least_squares
from held_observation_v1 import geometry

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
SOURCE = PROJECT / "visibility_boundary_v2/evidence/remote"
VIEWS = (2, 3, 4)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def inspect_result(result, points, basis):
    params = result.x
    axis = geometry.direction(params, basis)
    axial = (points - params[:3]) @ axis
    _, singular, vectors = np.linalg.svd(result.jac, full_matrices=False)
    weak = vectors[-1]
    return dict(cost=float(result.cost), success=bool(result.success), nfev=result.nfev,
                center=params[:3].tolist(), axis=axis.tolist(), radius=float(params[5]),
                half_length=float(params[6]), condition=float(singular[0]/max(singular[-1], 1e-15)),
                cap_negative=int(sum(axial < -params[6])), cap_positive=int(sum(axial > params[6])),
                weak_center_axial=float(weak[:3] @ axis), weak_half_length=float(weak[6]),
                singular_values=singular.tolist())


def trace(cloud):
    trials = []

    def solver(fun, initial, **kwargs):
        result = least_squares(fun, initial, **kwargs)
        points, basis = kwargs["args"]
        trial = inspect_result(result, points, basis)
        trial["initial"] = list(initial)
        trials.append(trial)
        return result

    with patch("scipy.optimize.least_squares", solver):
        fitted = geometry.fit(geometry.sample(cloud))
    return dict(fit=fitted, trials=trials)


def main():
    paths = [SOURCE / f"view_{index}/clouds.npz" for index in VIEWS]
    paths.append(PROJECT / "held_observation_v1/geometry.py")
    before = {str(p.relative_to(PROJECT)): sha(p) for p in paths}
    results = []
    for index in VIEWS:
        with np.load(SOURCE / f"view_{index}/clouds.npz") as arrays:
            value = trace(arrays["noise_0"])
        results.append(dict(index=index, **value))
        print(json.dumps(dict(index=index, trials=[{k: t[k] for k in
            ("cost", "condition", "half_length", "cap_negative", "cap_positive",
             "weak_center_axial", "weak_half_length")} for t in value["trials"]])))
    assert before == {str(p.relative_to(PROJECT)): sha(p) for p in paths}
    save(ROOT / "diagnosis.json", dict(versions=dict(python=platform.python_version(),
         numpy=np.__version__, scipy=scipy.__version__), inputs=before, results=results,
         input_hashes_unchanged=True, physical_attempts=0, model_calls=0, training_runs=0))


if __name__ == "__main__":
    main()
