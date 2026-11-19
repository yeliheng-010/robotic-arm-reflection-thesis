"""细长物体的观测内长轴候选。"""
from yc_candidates import candidates as original


def candidates(nominal, fitted):
    return original(nominal,fitted)
