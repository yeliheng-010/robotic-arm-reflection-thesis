from itertools import product
import numpy as np
from coverage_repair_v1.proposals import changed,camera_key
from held_observation_v1.common import CAMERA_BUDGET


def proposals(config,boxes):
    anchor=config['camera']
    bounds=np.asarray(list(boxes.values()))
    center=(bounds[:,0].min(axis=0)+bounds[:,1].max(axis=0))/2
    rows=[anchor]
    seen={camera_key(anchor)}
    for distance,azimuth,elevation in product((.08,.16,0.),(35.,-35.,45.,-45.),(0.,-5.,-12.)):
        camera=changed(anchor,np.array([azimuth,elevation,distance,5.,0.,0.]),center)
        if camera is None or camera_key(camera) in seen:
            continue
        rows.append(camera)
        seen.add(camera_key(camera))
        if len(rows)==CAMERA_BUDGET:
            break
    return rows
