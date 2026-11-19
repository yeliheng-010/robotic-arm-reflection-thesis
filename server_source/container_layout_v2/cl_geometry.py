"""编译场景检查实际坐标、桌面边界和碰撞体包围盒间距。"""
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from reflection.monitors import object_extents
from diversity.scene import apply_scene
from cl_design import SCENE, CONTAINERS, CLEARANCE, MIN_MOVE, configuration


def geom_bounds(model, data, gid):
    rotation=data.geom_xmat[gid].reshape(3,3)
    center=data.geom_xpos[gid]
    size=model.geom_size[gid]
    kind=int(model.geom_type[gid])
    if kind==int(mujoco.mjtGeom.mjGEOM_MESH):
        mid=model.geom_dataid[gid]
        start,count=model.mesh_vertadr[mid],model.mesh_vertnum[mid]
        vertices=model.mesh_vert[start:start+count]@rotation.T+center
        return vertices.min(axis=0),vertices.max(axis=0)
    if kind==int(mujoco.mjtGeom.mjGEOM_SPHERE):
        extent=np.repeat(size[0],3)
    elif kind==int(mujoco.mjtGeom.mjGEOM_BOX):
        extent=np.abs(rotation)@size
    elif kind==int(mujoco.mjtGeom.mjGEOM_CAPSULE):
        extent=size[0]+size[1]*np.abs(rotation[:,2])
    elif kind==int(mujoco.mjtGeom.mjGEOM_CYLINDER):
        extent=size[0]*np.sqrt(np.sum(rotation[:,:2]**2,axis=1))+size[1]*np.abs(rotation[:,2])
    elif kind==int(mujoco.mjtGeom.mjGEOM_ELLIPSOID):
        extent=np.sqrt(np.sum((rotation*size)**2,axis=1))
    else:
        raise ValueError('Unsupported collision geom: '+str(kind))
    return center-extent,center+extent


def body_bounds(model, data, bid):
    gids=np.flatnonzero((model.geom_bodyid==bid)&((model.geom_contype|model.geom_conaffinity)!=0))
    boxes=np.array([geom_bounds(model,data,int(g)) for g in gids])
    return boxes[:,0].min(axis=0),boxes[:,1].max(axis=0)


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
            boxes[body.name] = [v.tolist() for v in body_bounds(model, data, index)]
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
            if other in (name, 'simple_table'):
                continue
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
