from pathlib import Path
import traceback
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import mujoco
from cv_select import scene, evaluate
from cv_metrics import isolated_mask
from sd_config import MOVING
from cv_policy import REQUIRED
from sd_inventory import root_boxes
from sd_runtime import render
from grasp_process import camera_calibration_from_env
from pose_fresh_v1.observe import paused
from pose_fresh_v1.common import verify as verify_source
from surface_grasp_v1.common import read, save, sha
from depth_diagnostic_v1.numeric import samples, summary

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'pose_fresh_v1/run/978112'
RUN = ROOT / 'run'


def rays(env, rows, *, transform, intrinsics):
    output = []
    fx, fy, cx, cy = intrinsics
    for row in sorted(rows, key=lambda r: -r['outside_m'])[:10]:
        direction = np.array([(row['u']-cx)/fx, (row['v']-cy)/fy, 1.])
        norm = np.linalg.norm(direction)
        ray = transform[:3, :3] @ (direction/norm)
        gid = np.array([-1], dtype=np.int32)
        distance = mujoco.mj_ray(env.mj_model, env.mj_data, transform[:3, 3], ray,
            np.array([1, 1, 1, 0, 0, 0], dtype=np.uint8), 1, -1, gid)
        root = int(env.mj_model.body_rootid[env.mj_model.geom_bodyid[gid[0]]]) if gid[0] >= 0 else -1
        output.append(dict(row, ray_geom=int(gid[0]), ray_root=env.mj_model.body(root).name if root >= 0 else None,
            ray_distance_m=float(distance), ray_depth_m=float(distance/norm) if distance >= 0 else None))
    return output


def inspect(env, renderer):
    raw, roots = render(env), renderer.root_map(env.mj_data)
    transform, intrinsics = camera_calibration_from_env(env)
    boxes = root_boxes(env.mj_model, env.mj_data)
    rows, records, arrays = [], {}, dict(depth=raw['depth'], roots=roots)
    for name in MOVING:
        mask = roots == env.mj_model.body(name).id
        outline = isolated_mask(env, renderer, name)
        arrays[name] = outline
        variants = {str(k): samples(raw['depth'], mask, transform=transform.A,
                    intrinsics=intrinsics, box=boxes[name], kernel=k) for k in (3, 5, 7)}
        for row in variants['3']:
            row.update(name=name, inside_isolated=bool(outline[row['v'], row['u']]))
        records[name] = dict(variants=variants, isolated_pixels=int(outline.sum()))
        rows.extend(variants['3'])
    np.savez_compressed(RUN / 'pixels.npz', **arrays)
    return dict(records=records, original=summary(rows), worst_rays=rays(env, rows,
        transform=transform.A, intrinsics=intrinsics), transform=transform.A.tolist(),
        intrinsics=list(intrinsics), boxes=boxes,
        body_ids={name: int(env.mj_model.body(name).id) for name in MOVING})


def main():
    manifest = verify_source()
    RUN.mkdir(exist_ok=False)
    inputs = {str(p): sha(p) for p in SOURCE.iterdir() if p.is_file()}
    identities = dict(manifest['identities'])
    identities.update({str(p): sha(p) for p in ROOT.iterdir() if p.is_file()})
    save(RUN / 'started.json', dict(inputs=inputs, identities=identities))
    try:
        old = read(SOURCE / 'selection.json')['attempts'][239]
        config = manifest['configs']['978112']
        with scene(config) as (env, renderer):
            with np.load(SOURCE / 'initial_state.npz') as data:
                mujoco.mj_setState(env.mj_model, env.mj_data, data['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
            mujoco.mj_forward(env.mj_model, env.mj_data)
            with paused(env, RUN):
                boxes = root_boxes(env.mj_model, env.mj_data)
                report = evaluate(env, renderer, old['camera'], boxes={n: boxes[n] for n in REQUIRED})
                result = inspect(env, renderer)
        result.update(reproduced_measurements=report['measurements'] == old['measurements'],
            reproduced_calibration=report['calibration'] == old['calibration'], old_calibration=old['calibration'],
            current_calibration=report['calibration'], private_only=True, task_motion_attempts=0,
            pixels_sha256=sha(RUN / 'pixels.npz'))
        assert result['original'] == report['calibration']
        assert all(sha(p) == digest for p, digest in inputs.items())
        save(RUN / 'result.json', result)
        print({k: v for k, v in result.items() if k not in ('records', 'boxes', 'worst_rays')}, flush=True)
    except Exception:
        save(RUN / 'failure.json', dict(traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
