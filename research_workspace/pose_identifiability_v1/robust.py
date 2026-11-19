"""消融后选用的最小候选：孤立点筛选+原5起点拟合；尚未接入执行。"""
from held_observation_v1.geometry import fit as original_fit
from pose_identifiability_v1.candidate import observed_inliers


def fit(points):
    filtered, filtering = observed_inliers(points)
    return dict(original_fit(filtered), filtering=filtering)
