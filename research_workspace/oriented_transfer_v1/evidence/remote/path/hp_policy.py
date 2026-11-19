"""只允许首抬升样本保留原已存在的支撑接触。"""
from guard_policy import SUPPORTS

NUMERIC_DISTANCE_M=1e-9


def allowed_initial(contact, baseline, *, first_sample):
    if not first_sample or not any(r.startswith(SUPPORTS) for r in contact['roots']):
        return False
    key=sorted(contact['roots'])
    return any(sorted(row['roots'])==key and contact['distance']>=row['distance']-NUMERIC_DISTANCE_M
        for row in baseline)
