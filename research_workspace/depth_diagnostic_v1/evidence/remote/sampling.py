from pathlib import Path
import traceback
from itertools import product
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import mujoco
from cv_select import scene
from sf_select import set_camera
from pose_fresh_v1.observe import paused
from surface_grasp_v1.common import read, save, sha
from depth_diagnostic_v1.worker import ROOT, RUN, SOURCE, rays
from depth_diagnostic_v1.numeric import samples, summary

OUTPUT = ROOT / 'sampling'


def rendered(env, count):
    model = env.mj_model
    original = model.vis.quality.offsamples
    model.vis.quality.offsamples = count
    renderer = None
    try:
        renderer = mujoco.Renderer(model, env.height, env.width)
        renderer.enable_depth_rendering()
        renderer.update_scene(env.mj_data, 'cam')
        depth = renderer.render().copy()
        renderer.disable_depth_rendering()
        renderer.enable_segmentation_rendering()
        renderer.update_scene(env.mj_data, 'cam')
        segmentation = renderer.render().copy()
        roots = np.full(depth.shape, -1, dtype=np.int32)
        valid = (segmentation[..., 0] >= 0) & (segmentation[..., 1] == int(mujoco.mjtObj.mjOBJ_GEOM))
        roots[valid] = model.body_rootid[model.geom_bodyid[segmentation[..., 0][valid]]]
        context = renderer._mjr_context
        actual = int(context.offSamples)
        return depth, roots, actual
    finally:
        if renderer is not None:
            renderer.close()
        model.vis.quality.offsamples = original


def metrics(depth, roots, reference):
    rows = []
    for name, bid in reference['body_ids'].items():
        values = samples(depth, roots == bid, transform=np.asarray(reference['transform']),
            intrinsics=reference['intrinsics'], box=reference['boxes'][name], kernel=3)
        rows.extend(dict(row, name=name) for row in values)
    return dict(summary=summary(rows), outliers=[r for r in rows if r['outside_m'] > .006])


def compare(env, reference):
    result = {}
    with np.load(RUN / 'pixels.npz') as data:
        old_depth, old_roots = data['depth'], data['roots']
    original_samples = int(env.mj_model.vis.quality.offsamples)
    for label, count in (('original', original_samples), ('no_msaa', 0)):
        depth, roots, actual = rendered(env, count)
        np.savez_compressed(OUTPUT / f'{label}.npz', depth=depth, roots=roots)
        result[label] = dict(requested_samples=count, actual_samples=actual,
            same_depth_as_archived=bool(np.array_equal(depth, old_depth)),
            same_roots_as_archived=bool(np.array_equal(roots, old_roots)),
            fixed_old_mask=metrics(depth, old_roots, reference), native_mask=metrics(depth, roots, reference),
            focus_depth_m=float(depth[534, 481]), focus_root=int(roots[534, 481]),
            arrays_sha256=sha(OUTPUT / f'{label}.npz'))
    focus = reference['worst_rays'][0]
    points = [dict(focus, u=focus['u']+x, v=focus['v']+y) for x, y in product((-.5, 0., .5), repeat=2)]
    return dict(variants=result, pixel_center_rays=rays(env, points,
        transform=np.asarray(reference['transform']), intrinsics=reference['intrinsics']))


def main():
    assert read(RUN / 'audit_v2.json')['passed']
    OUTPUT.mkdir(exist_ok=False)
    paths = [RUN / 'pixels.npz', RUN / 'result.json', RUN / 'audit_v2.json', SOURCE / 'initial_state.npz',
             SOURCE / 'selection.json', ROOT.parent / 'pose_fresh_v1/run/manifest.json']
    paths.extend(p for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch'))
    inputs = {str(p): sha(p) for p in paths}
    save(OUTPUT / 'started.json', dict(inputs=inputs))
    try:
        reference = read(RUN / 'result.json')
        manifest = read(ROOT.parent / 'pose_fresh_v1/run/manifest.json')
        camera = read(SOURCE / 'selection.json')['attempts'][239]['camera']
        with scene(manifest['configs']['978112']) as (env, renderer):
            with np.load(SOURCE / 'initial_state.npz') as data:
                mujoco.mj_setState(env.mj_model, env.mj_data, data['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
            mujoco.mj_forward(env.mj_model, env.mj_data)
            with paused(env, OUTPUT):
                set_camera(env, camera)
                result = compare(env, reference)
        assert all(sha(p) == digest for p, digest in inputs.items())
        save(OUTPUT / 'result.json', result)
        print(result, flush=True)
    except Exception:
        save(OUTPUT / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
