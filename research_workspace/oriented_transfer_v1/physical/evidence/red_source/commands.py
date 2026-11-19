"""RED：旧执行器仍固定抓取朝向。"""
import numpy as np
import spatialmath as sm
from waypoint_paths import cartesian


def build(selected, minimum):
    grasp=sm.SE3(np.array(selected['prefix']['pose']))
    lifted=sm.SE3.Trans(0,0,selected['lift'])*grasp
    target=sm.SE3.Rt(grasp.R,np.array(selected['goal']['release'])[:3,3])
    return [cartesian(grasp,lifted,minimum),cartesian(lifted,target,minimum)],[minimum,minimum],(lifted,target,target)
