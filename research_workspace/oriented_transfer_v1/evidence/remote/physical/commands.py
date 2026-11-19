"""实际执行使用已审计的抬升和连续关节轨迹。"""
import numpy as np
import spatialmath as sm
from waypoint_paths import cartesian
from rh_planner import planners


def build(selected, minimum):
    grasp=sm.SE3(np.array(selected['prefix']['pose']))
    lifted=sm.SE3.Trans(0.,0.,selected['lift'])*grasp
    release=sm.SE3(np.array(selected['goal']['release']))
    paths=[cartesian(grasp,lifted,minimum),*planners(selected['route'])]
    times=[minimum,*selected['route']['durations']]
    return paths,times,(lifted,release,release)
