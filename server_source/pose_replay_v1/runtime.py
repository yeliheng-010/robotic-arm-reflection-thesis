"""只处理观测点；沿用原质量与双视角一致性规则。"""
import numpy as np
from held_observation_v1.geometry import sample, consistency
from pose_identifiability_v1.robust import fit
from visibility_calibration_v1.analysis import single_quality


def full_p95(points, fitted):
    relative = points - fitted["center"]
    axis = np.asarray(fitted["axis"])
    axial = np.clip(relative @ axis, -fitted["half_length"], fitted["half_length"])
    residual = np.linalg.norm(relative - axial[:, None] * axis, axis=1) - fitted["radius"]
    return float(np.percentile(np.abs(residual), 95))


def single(cloud):
    try:
        points = sample(cloud)
        fitted = fit(points)
        return dict(fit=fitted, quality_passed=bool(single_quality(fitted)), failure=None,
                    full_cloud_p95_m=full_p95(points, fitted))
    except (ValueError, AssertionError) as error:
        return dict(fit=None, quality_passed=False, failure=str(error), full_cloud_p95_m=None)


def pair(clouds, singles):
    if any(row["fit"] is None for row in singles):
        return dict(fit=None, quality_passed=False, failure="single_fit_unavailable")
    try:
        points = sample(np.vstack([sample(cloud) for cloud in clouds]))
        combined = fit(points)
        quality = consistency([combined, *[row["fit"] for row in singles]])
        return dict(fit=combined, quality_passed=quality["passed"], quality=quality,
                    failure=None, full_cloud_p95_m=full_p95(points, combined))
    except (ValueError, AssertionError) as error:
        return dict(fit=None, quality_passed=False, failure=str(error))
