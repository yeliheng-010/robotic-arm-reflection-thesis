"""根据完整 MuJoCo 场景和已核验初态检查障碍间距，而非只检查四个目标。"""
import hashlib
import json
import mujoco
import numpy as np
from reflection.monitors import object_extents

BODY_X = 1.3575
BODY_Y = .84
HALF_X = .0375
HALF_Y = .012
BASE_Z = .74
MAX_HALFHEIGHT = .22
MIN_CLEARANCE = .008


def inspect(root):
    scene = root.parent/'improvement_20261019/code/manipulator_grasp/assets/scenes/scene.xml'
    baseline = root.parent/'refinement_v2/collision/24_0/result.json'
    model = mujoco.MjModel.from_xml_path(str(scene))
    data = mujoco.MjData(model)
    record = json.loads(baseline.read_text())['records'][0]
    data.qpos[:] = record['candidate_trace']['initial_qpos']
    mujoco.mj_forward(model, data)
    box_low = np.array([BODY_X-HALF_X, BODY_Y-HALF_Y, BASE_Z])
    box_high = np.array([BODY_X+HALF_X, BODY_Y+HALF_Y, BASE_Z+2*MAX_HALFHEIGHT])
    rows = []
    for index in range(1, model.nbody):
        body = model.body(index)
        if body.geomnum == 0 or body.name == 'SafetyDivider':
            continue
        start, count = int(model.body_geomadr[index]), int(model.body_geomnum[index])
        geoms = slice(start, start+count)
        if not np.any(model.geom_contype[geoms] | model.geom_conaffinity[geoms]):
            continue
        low, high = object_extents(model, data, index)
        if body.name == 'simple_table':
            assert abs(float(high[2])-BASE_Z) < 1e-8
            continue
        gaps = np.maximum(box_low-high, low-box_high)
        clearance = float(max(gaps))
        rows.append(dict(body=body.name, clearance=clearance))
    blockers = [r for r in rows if r['clearance'] < MIN_CLEARANCE]
    assert not blockers, 'Full-scene overlap: '+str(blockers)
    return dict(passed=True, checked_bodies=len(rows), rows=rows, low=box_low.tolist(), high=box_high.tolist(),
                baseline=str(baseline), baseline_sha256=hashlib.sha256(baseline.read_bytes()).hexdigest(),
                excluded_supports=['simple_table'], noncolliding_visuals_ignored=True,
                replaced_obstacle='SafetyDivider')
