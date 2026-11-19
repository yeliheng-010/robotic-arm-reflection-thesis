"""独立进程恢复完整状态复测；不触发任务、模型或相机搜索。"""
import numpy as np
import mujoco
import cv2
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from cv_rgb import compare
from cv_policy import frame_gate
from sd_inventory import root_boxes
from sf_camera import framed
from sensor_independent_v1.sensor import paired, capture, rgb
from observation_search_v1.stable import settle, decode, check_record
from diversity.noise import corrupt_depth
from qualified_task_v1.common import ROOT, RUN, PILOT, read, save, sha, verify


def recover(config, state, *, original, folder):
    with scene(config) as (env, segment):
        mujoco.mj_setState(env.mj_model, env.mj_data, state, mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        report = read(original/'qualification.json')
        boxes = root_boxes(env.mj_model, env.mj_data)
        framing = framed({n: boxes[n] for n in report['measurements']}, config['camera'])
        assert framing == report['framing']
        frames, stability = settle(lambda: rgb(env))
        assert stability['passed']
        with paired(env, segment) as (resources, samples):
            current = capture(env, resources['no_msaa'], framing)
        post = rgb(env)
        assert compare(frames[-1], post)['passed']
        assert current['report']['measurements'] == report['measurements']
        assert frame_gate(report['measurements']) == report['gate']
        assert current['report']['calibration'] == report['calibration']
        assert current['report']['accepted'] and report['accepted']
        with np.load(original/'qualified_sensor.npz') as saved:
            np.testing.assert_array_equal(saved['depth'], current['depth'])
            match = compare(saved['img'], post)
            assert match['passed'], match
            image = saved['img'].copy()
        with (folder/'private_roots.npz').open('xb') as stream:
            np.savez_compressed(stream, roots=current['roots'])
        body_ids = {n: int(env.mj_model.body(n).id) for n in report['measurements']}
    return dict(rgb=match, samples=samples, body_ids=body_ids), image, current['depth']


def audit(seed, case):
    original = RUN/f'initial_v2/{seed}/initial_observation'
    folder = RUN/f'audit/{seed}'
    folder.mkdir(parents=True, exist_ok=False)
    with np.load(original/'rgb_0.npz') as raw:
        frames = decode(raw)
    report = read(original/'qualification.json')
    check_record(frames[:-1], report['rgb']['stability'])
    assert compare(frames[-2], frames[-1])['passed']
    with np.load(original/'source_state.npz') as data:
        state = data['state'].copy()
    with np.load(RUN/f'{seed}/initial_observation/source_state.npz') as failed:
        np.testing.assert_array_equal(state, failed['state'])
    checked, image, clean = recover(case['config'], state, original=original, folder=folder)
    noisy, noise = corrupt_depth(clean, case['config']['sensor'], seed=np.random.SeedSequence([seed, 301, 1, 0]))
    assert cv2.imwrite(str(folder/'qualified.png'), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    with (folder/'public_sensor.npz').open('xb') as stream:
        np.savez_compressed(stream, img=image, depth=noisy)
    result = dict(passed=True, seed=seed, replay=checked, noise=noise,
        source_sha256=sha(original/'qualified_sensor.npz'), image_sha256=sha(folder/'qualified.png'),
        public_sensor_sha256=sha(folder/'public_sensor.npz'), physical_attempts=0, model_calls=0,
        training_runs=0, noise_applied_once=True, camera_searches=0)
    save(folder/'result.json', result)
    return result


def main():
    manifest = verify()
    paths = [ROOT/'audit.py', ROOT/'audit.sbatch']
    sources = {str(p): sha(p) for p in paths}
    save(RUN/'audit_manifest.json', dict(sources=sources, parent_sha256=sha(RUN/'manifest.json'),
        input_identities={str(p): sha(p) for p in (RUN/'initial_v2').rglob('*') if p.is_file()},
        physical_attempts=0, model_calls=0, training_runs=0))
    rows = [audit(seed, manifest['cases'][str(seed)]) for seed in PILOT]
    verify()
    save(RUN/'audit_result.json', dict(passed=True, rows=rows, independent_process=True))
    print(dict(passed=True, qualified=len(rows), physical_attempts=0), flush=True)


if __name__ == '__main__':
    main()
