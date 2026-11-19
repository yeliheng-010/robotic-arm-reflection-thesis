from reflection.__main__ import bootstrap
bootstrap()
from cv_policy import frame_gate
from sf_camera import framed
from camera_joint_v1.search import global_camera
from camera_joint_v1.candidates import local
from pose_fresh_v1.audit import check_state, check_fits
from pose_fresh_v1.evaluate import annotate, summarize
import json
import numpy as np
from sensor_independent_v1 import assessment, audit_arrays
from sensor_independent_v2.rgb_policy import assess, qualify
from sensor_independent_v2.common import RUN, METHODS, SEEDS, NOISE_PREFIX, read, save, sha, verify


def check_sequence(rows, *, config, boxes, folder):
    assert 128 <= len(rows) <= 256
    original = [dict(index=r['index'], camera=r['camera'], **r['methods']['original'])
                for r in rows[:128] if 'methods' in r]
    generated = list(local(original, boxes)) if original else []
    if original:
        assert len(rows) == 128 + len(generated)
    for index, row in enumerate(rows):
        assert row['index'] == index
        if row['stage'] != 'local':
            assert row['camera'] == global_camera(config, boxes, row['proposal_index'])
        else:
            assert all(row[k] == generated[index-128][k] for k in ('camera', 'anchor_index', 'offset_index', 'delta'))
        if row['camera'] is not None:
            assert framed(boxes, row['camera']) == row['framing']
        if 'methods' in row:
            with np.load(folder / f'rgb_{index}.npz') as arrays:
                assert assess(arrays['before'], arrays['after']) == row['rgb']
            for value in row['methods'].values():
                assert frame_gate(value['measurements']) == value['gate']
                assert qualify(value, row['rgb']) == value


def check_pose(folder, result, seed):
    fits, views = read(folder / 'fits.json'), read(folder / 'views.json')
    assert len(fits['singles']) == 3 and not fits['pairs']
    assert len(views) == 1 and views[0]['full_frame_qualified']
    metadata = read(folder / 'view_0/metadata.json')
    assert sha(folder / 'view_0/clouds.npz') == metadata['clouds_sha256']
    assert [r['seed'] for r in metadata['samples']] == [[NOISE_PREFIX, seed, 0, 0, i] for i in range(3)]
    checks = check_fits(folder, fits)
    errors = annotate(fits, views, read(folder / 'private_truth.json'))
    assert errors == read(folder / 'private_errors.json')
    assert summarize(errors) == result['metrics']
    assert sha(folder / 'fits.json') == result['fits_before_evaluation_sha256']
    return errors, checks


def layout(seed, config):
    folder = RUN / str(seed)
    result = read(folder / 'result.json')
    for name, digest in result['evidence'].items():
        assert sha(folder / name) == digest, name
    if not result['geometry_accepted']:
        return result, {}, {}, []
    check_state(folder)
    assert result['actual_samples'] == dict(rgb=4, original_depth=4, original_segmentation=4,
                                           no_msaa_depth=0, no_msaa_segmentation=0)
    rows = read(folder / 'observations.json')
    journal = [json.loads(s) for s in (folder / 'observations.jsonl').read_text(encoding='utf-8').splitlines()]
    assert journal == rows
    check_sequence(rows, config=config, boxes=read(folder / 'boxes.json'), folder=folder)
    measured = [r['index'] for r in rows if 'methods' in r]
    assert len(measured) == result['measured'] and measured[:3] == result['diagnostic_indices']
    errors, checks = {}, {}
    for method in METHODS:
        accepted = [r['index'] for r in rows if r.get('methods', {}).get(method, {}).get('accepted')]
        assert bool(accepted) == (method in result['accepted'])
        if accepted:
            assert accepted[0] == result['accepted'][method]['index']
            errors[method], checks[method] = check_pose(folder / method, result['accepted'][method], seed)
    rays = audit_arrays.check_layout(folder, config, result['diagnostic_indices'])
    result.update(pair_statistics=assessment.paired_counts(rows), ray_statistics=assessment.ray_metrics(rays))
    result['rgb_failures'] = sum(not r['rgb']['passed'] for r in rows if 'rgb' in r)
    result['rgb_nonidentical'] = sum(not r['rgb']['bitwise_equal'] for r in rows if 'rgb' in r)
    return result, errors, checks, rays


def main():
    manifest = verify()
    layouts, checks, all_rays = {}, {}, []
    combined = {method: dict(singles=[], pairs=[]) for method in METHODS}
    for seed in SEEDS:
        result, errors, checked, rays = layout(seed, manifest['configs'][str(seed)])
        layouts[str(seed)], checks[str(seed)] = result, checked
        all_rays.extend(rays)
        for method, values in errors.items():
            combined[method]['singles'].extend(values['singles'])
    qualified = {m: [s for s, r in layouts.items() if m in r.get('accepted', {})] for m in METHODS}
    metrics = {m: summarize(v) for m, v in combined.items()}
    gained = sorted(set(qualified['no_msaa']) - set(qualified['original']))
    lost = sorted(set(qualified['original']) - set(qualified['no_msaa']))
    valid = [r for r in layouts.values() if r.get('diagnostic_indices')]
    coverage = len(valid) >= 8 and sum(len(r['diagnostic_indices']) for r in valid) >= 24
    rays_ok = all(assessment.ray_nonregression(r['ray_statistics']) for r in valid)
    calibration_losses = sum(r['pair_statistics']['calibration']['lost'] for r in valid)
    false = metrics['no_msaa']['singles']['qualified']['selective']['false_accepted']
    rgb_failures = sum(r.get('rgb_failures', 0) for r in layouts.values())
    verify()
    result = dict(passed=True, independent_process=True, layouts=layouts, checks=checks,
        qualified=qualified, gained=gained, lost=lost, metrics=metrics,
        diagnostic_coverage_sufficient=coverage, ray_nonregression=rays_ok,
        calibration_losses=calibration_losses, rgb_failures=rgb_failures,
        ray_statistics=assessment.ray_metrics(all_rays),
        next_integration_gate=coverage and len(qualified['no_msaa']) >= 8 and not lost and false == 0
            and rays_ok and calibration_losses == 0 and rgb_failures == 0,
        control_deployed=False, task_motion_attempts=0,
        model_calls=0, training_runs=0, inputs_unchanged=True)
    save(RUN / 'audit.json', result)
    print({k: v for k, v in result.items() if k not in ('layouts', 'checks', 'metrics')}, flush=True)


if __name__ == '__main__':
    main()
