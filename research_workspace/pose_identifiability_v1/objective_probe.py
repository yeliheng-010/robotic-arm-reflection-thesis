"""用相邻观测拟合作审计参考，评价同一失败点云的残差与代价。"""
import json
import numpy as np
from scipy.spatial import cKDTree
from held_observation_v1.geometry import sample
from pose_identifiability_v1.diagnose import ROOT, SOURCE, save


def errors(points, fitted):
    axis = np.asarray(fitted["axis"])
    relative = points - fitted["center"]
    axial = np.clip(relative @ axis, -fitted["half_length"], fitted["half_length"])
    return np.linalg.norm(relative - axial[:, None] * axis, axis=1) - fitted["radius"]


def main():
    rows = json.loads((ROOT / "diagnosis.json").read_text(encoding="utf-8"))["results"]
    reference = rows[0]["fit"]
    result = []
    for row in rows:
        index = row["index"]
        with np.load(SOURCE / f"view_{index}/clouds.npz") as arrays:
            points = sample(arrays["noise_0"])
        fits = {"own": row["fit"], "neighbor_observed": reference}
        costs = {}
        for name, fitted in fits.items():
            residual = errors(points, fitted)
            squared = (residual / .003) ** 2
            costs[name] = dict(soft_l1=float(.003 ** 2 * np.sum(np.sqrt(1 + squared) - 1)),
                               cauchy=float(.5 * .003 ** 2 * np.sum(np.log1p(squared))),
                               residual_percentiles_m=np.percentile(np.abs(residual), [50, 95, 99, 100]).tolist())
        distances, _ = cKDTree(points).query(points, k=7)
        result.append(dict(index=index, costs=costs,
                           neighbor_distance_percentiles_m=np.percentile(distances[:, -1], [50, 95, 99, 100]).tolist()))
    save(ROOT / "objective_probe.json", dict(results=result,
         scope="Neighbor fit only for diagnosis, never candidate initialization or ground truth"))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
