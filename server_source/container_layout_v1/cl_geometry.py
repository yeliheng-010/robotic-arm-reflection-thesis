"""编译场景检查实际坐标、桌面边界和碰撞体包围盒间距。"""
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from reflection.monitors import object_extents
from diversity.scene import apply_scene
from cl_design import SCENE, CONTAINERS, CLEARANCE, MIN_MOVE, configuration


def compiled(config=None):
    spec = mujoco.MjSpec.from_file(str(SCENE))
    if config is not None:
        apply_scene(spec, config)
    for name in ('safety_divider', 'safety_divider_marker_left', 'safety_divider_marker_right'):
        geom = spec.geom(name)
        geom.contype, geom.conaffinity = 0, 0
        geom.rgba = [0, 0, 0, 0]
    model = spec.compile()
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def inventory():
    model, data = compiled()
    centers, boxes = {}, {}
    for index in range(1, model.nbody):
        body = model.body(index)
        start, count = int(model.body_geomadr[index]), int(model.body_geomnum[index])
        if count and np.any(model.geom_contype[start:start+count] | model.geom_conaffinity[start:start+count]):
            boxes[body.name] = [v.tolist() for v in object_extents(model, data, index)]
        if body.name in CONTAINERS:
            centers[body.name] = data.xpos[index].tolist()
    return dict(centers=centers, boxes=boxes, table=boxes['simple_table'])


def translated_boxes(positions, geometry):
    boxes = {name: np.array(value) for name, value in geometry['boxes'].items()}
    for name in CONTAINERS:
        delta = np.array(positions[name])-geometry['centers'][name][:2]
        boxes[name][:, :2] += delta
    return boxes


def changed_order(positions, geometry):
    original = geometry['centers']
    return any((positions[a][axis]-positions[b][axis]) *
               (original[a][axis]-original[b][axis]) < 0
               for i, a in enumerate(CONTAINERS) for b in CONTAINERS[i+1:] for axis in (0, 1))


def check_positions(positions, geometry, *, require_move):
    boxes = translated_boxes(positions, geometry)
    table = np.array(geometry['table'])
    problems = []
    for name in CONTAINERS:
        low, high = boxes[name]
        if np.any(low[:2] < table[0, :2]+CLEARANCE) or np.any(high[:2] > table[1, :2]-CLEARANCE):
            problems.append(name+':outside_table')
        if require_move and np.linalg.norm(np.array(positions[name])-geometry['centers'][name][:2]) < MIN_MOVE:
            problems.append(name+':movement_too_small')
        for other, (other_low, other_high) in boxes.items():
            if other not in (name, 'simple_table'):
                gap = float(np.max(np.maximum(low-other_high, other_low-high)))
                if gap < CLEARANCE:
                    problems.append(name+':too_close:'+other)
    if require_move and not changed_order(positions, geometry):
        problems.append('relative_order_unchanged')
    return dict(passed=not problems, problems=problems)


def verify_compiled(item, layout, geometry):
    model, data = compiled(configuration(item, layout))
    positions = {n: data.xpos[model.body(n).id][:2].tolist() for n in CONTAINERS}
    expected = layout['positions'] if item['arm']=='randomized' else {
        n: geometry['centers'][n][:2] for n in CONTAINERS}
    for name in CONTAINERS:
        np.testing.assert_allclose(expected[name], positions[name], atol=1e-12, rtol=0)
    return dict(positions=positions, body_ids={n: int(model.body(n).id) for n in CONTAINERS},
                checks=check_positions(positions, geometry, require_move=item['arm']=='randomized'))
