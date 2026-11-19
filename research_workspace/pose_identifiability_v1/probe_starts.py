"""有界初始化诊断；仅用观测点，保存所有解以区分搜索与目标函数退化。"""
from unittest.mock import patch
import json
import numpy as np
from pose_identifiability_v1 import candidate
from pose_identifiability_v1.diagnose import ROOT, SOURCE, inspect_result, save
from held_observation_v1.geometry import sample


def main():
    with np.load(SOURCE / "view_3/clouds.npz") as arrays:
        points = sample(arrays["noise_0"])
    trials = []
    solver = candidate.least_squares

    def wrapped(fun, initial, **kwargs):
        result = solver(fun, initial, **kwargs)
        cloud, basis = kwargs["args"]
        record = inspect_result(result, cloud, basis)
        record["initial"] = list(initial)
        trials.append(record)
        return result

    with patch.object(candidate, "least_squares", wrapped):
        result = candidate.fit_multistart(points)
    save(ROOT / "probe_starts.json", dict(fit=result, trials=trials))
    for index, trial in enumerate(trials):
        print(json.dumps(dict(index=index, **{key: trial[key] for key in
              ("cost", "condition", "half_length", "cap_negative", "cap_positive")})))


if __name__ == "__main__":
    main()
