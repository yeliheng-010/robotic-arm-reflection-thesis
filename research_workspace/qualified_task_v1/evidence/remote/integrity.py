"""对运行环境可访问的积分、派生缓存和渲染状态逐字段做指纹。"""
import hashlib
import random
import pickle
import numpy as np


def digest(value):
    return hashlib.sha256(value).hexdigest()


def fields(obj, *, prefix='', depth=0):
    result = {}
    for name in dir(obj):
        if name.startswith('_'):
            continue
        value = getattr(obj, name)
        key = prefix + name
        if isinstance(value, np.ndarray):
            result[key] = digest(value.tobytes())
        elif isinstance(value, (str, bytes, int, float, bool)):
            result[key] = repr(value)
        elif depth < 3 and type(value).__module__.startswith('mujoco'):
            result.update(fields(value, prefix=key+'.', depth=depth+1))
    return result


def fingerprint(env):
    result = dict(model=fields(env.mj_model), data=fields(env.mj_data))
    for name in ('mj_renderer', 'mj_depth_renderer'):
        renderer = getattr(env, name, None)
        if renderer is not None:
            result[name] = render_fields(renderer.scene)
    result['environment'] = {name: repr(getattr(env, name, None))
                            for name in ('width', 'height', 'fovy', 'camera_id', 'camera_name')}
    result['rng'] = digest(pickle.dumps((random.getstate(), np.random.get_state())))
    return result


def render_fields(scene):
    result = fields(scene)
    collections = dict(geoms=scene.geoms[:scene.ngeom], camera=scene.camera,
                       lights=scene.lights[:scene.nlight])
    for name, entries in collections.items():
        for index, entry in enumerate(entries):
            result.update(fields(entry, prefix=f'{name}.{index}.'))
    return result


def unchanged(before, after):
    differences = [name for name in set(before) | set(after) if before.get(name) != after.get(name)]
    if differences:
        raise AssertionError('Live observation mutated: '+', '.join(differences))
    return dict(passed=True, sections=list(before),
                fields=sum(len(v) for v in before.values() if isinstance(v, dict)))
