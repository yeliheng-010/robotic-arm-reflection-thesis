import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from cv_policy import frame_gate
from sf_camera import framed
from pose_fresh_v1.audit import check_state, check_fits
from pose_fresh_v1.evaluate import annotate, summarize
from camera_joint_v1.search import global_camera
from camera_joint_v1.candidates import local
from camera_joint_v1.policy import SEEDS, NOISE_PREFIX
from camera_joint_v1.common import RUN, read, save, sha, verify


def check_search(rows, *, config, boxes, method):
    assert 1 <= len(rows) <= 256
    assert not any(r['accepted'] for r in rows[:-1])
    local_rows = [r for r in rows if r['stage'] == 'local']
    if local_rows:
        assert len(rows) > 128 and method == 'joint'
        expected = list(local(rows[:128], boxes))[:len(local_rows)]
        assert len(expected) == len(local_rows)
        for actual, generated in zip(local_rows, expected):
            for key in ('camera', 'anchor_index', 'offset_index', 'delta'):
                assert actual[key] == generated[key]
    for index, row in enumerate(rows):
        assert row['index'] == index
        if row['stage'] != 'local':
            assert row['camera'] == global_camera(config, boxes, row['proposal_index'])
        if row['camera'] is None:
            assert not row['accepted']
            continue
        assert framed(boxes, row['camera']) == row['framing']
        if 'gate' in row:
            assert frame_gate(row['measurements']) == row['gate']
            assert row['accepted'] == bool(row['gate']['passed'] and row.get('calibration', {}).get('passed'))


def check_pose(folder, result, seed):
    fits, views = read(folder / 'fits.json'), read(folder / 'views.json')
    assert len(views) == 1 and views[0]['full_frame_qualified']
    assert frame_gate(views[0]['report']['measurements'])['passed']
    assert views[0]['calibration_passed']
    metadata = read(folder / 'view_0/metadata.json')
    assert sha(folder / 'view_0/clouds.npz') == metadata['clouds_sha256']
    assert len(fits['singles']) == 3 and not fits['pairs']
    for repeat, row in enumerate(metadata['samples']):
        assert row['seed'] == [NOISE_PREFIX, seed, 0, 0, repeat]
    checked = check_fits(folder, fits)
    errors = annotate(fits, views, read(folder / 'private_truth.json'))
    assert errors == read(folder / 'private_errors.json')
    assert summarize(errors) == result['metrics']
    assert sha(folder / 'fits.json') == result['fits_before_evaluation_sha256']
    return errors, checked


def layout(seed, config):
    folder = RUN / str(seed)
    result = read(folder / 'result.json')
    for name, digest in result['evidence'].items():
        assert sha(folder / name) == digest
    errors, checks = {}, {}
    if not result['geometry_accepted']:
        return result, errors, checks
    check_state(folder)
    boxes = read(folder / 'boxes.json')
    for method, stats in result['methods'].items():
        output = folder / method
        selection = read(output / 'selection.json')
        rows = selection['attempts']
        check_search(rows, config=config, boxes=boxes, method=method)
        assert selection['accepted'] == stats['qualified'] == rows[-1]['accepted']
        assert len(rows) == stats['candidates']
        assert sum('gate' in r for r in rows) == stats['measured']
        if stats['qualified']:
            errors[method], checks[method] = check_pose(output, stats, seed)
    return result, errors, checks


def main():
    manifest = verify()
    layouts, checks = {}, {}
    combined = {method: dict(singles=[], pairs=[]) for method in manifest['methods']}
    for seed in SEEDS:
        result, errors, checked = layout(seed, manifest['configs'][str(seed)])
        layouts[str(seed)], checks[str(seed)] = result, checked
        for method, values in errors.items():
            combined[method]['singles'].extend(values['singles'])
    qualified = {m: [s for s, r in layouts.items() if r['methods'].get(m, {}).get('qualified')]
                 for m in combined}
    gained = sorted(set(qualified['joint']) - set(qualified['original']))
    lost = sorted(set(qualified['original']) - set(qualified['joint']))
    metrics = {m: summarize(values) for m, values in combined.items()}
    errors = metrics['joint']['singles']['qualified']['selective']['false_accepted']
    verify()
    result = dict(passed=True, layouts=layouts, checks=checks, qualified=qualified,
        gained=gained, lost=lost, metrics=metrics, independent_process=True,
        next_validation_gate=len(qualified['joint']) >= 8 and not lost and errors == 0,
        control_deployed=False, physical_success_rate=None, task_motion_attempts=0,
        model_calls=0, training_runs=0, inputs_unchanged=True)
    save(RUN / 'audit.json', result)
    print({k: v for k, v in result.items() if k not in ('layouts', 'checks', 'metrics')}, flush=True)


if __name__ == '__main__':
    main()
