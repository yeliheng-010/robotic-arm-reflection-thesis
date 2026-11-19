"""观测内的小角度竖直抓取候选。"""
from cp_candidates import candidates as original


def candidates(nominal, fitted):
    return original(nominal,fitted)
