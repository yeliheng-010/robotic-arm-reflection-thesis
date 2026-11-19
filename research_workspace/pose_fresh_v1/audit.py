"""独立进程复算预先指定样本；全量核对选择、分类、来源及状态。"""
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from cv_policy import frame_gate
from pose_selective_v1.policy import choose
from pose_fresh_v1 import estimate, evaluate
from pose_fresh_v1.policy import SEEDS, REPEATS, NOISE_PREFIX, pairs
from pose_fresh_v1.common import RUN, read, save, sha, verify


def clouds(folder, row):
    indices = row.get('indices', [row.get('index')])
    result = []
    for index in indices:
        with np.load(folder / f'view_{index}/clouds.npz') as data:
            result.append(data[f'noise_{row["repeat"]}'])
    return result


def check_fits(folder, fits):
    checked = []
    selected = [('singles', fits['singles'][i]) for i in sorted({0, len(fits['singles']) - 1})] if fits['singles'] else []
    selected += [('pairs', fits['pairs'][0])] if fits['pairs'] else []
    for kind, row in selected:
        values = clouds(folder, row)
        actual = (estimate.single(values[0]) if kind == 'singles'
                  else estimate.pair(values, [estimate.single(c) for c in values]))
        assert estimate.selected(actual) == {k: row[k] for k in ('original', 'repaired', 'choice')}
        checked.append(dict(kind=kind, indices=row.get('indices', [row.get('index')]), repeat=row['repeat']))
    for row in fits['singles'] + fits['pairs']:
        assert choose(row['original']['quality_passed'], row['repaired']['quality_passed']) == row['choice']
    return checked


def check_views(folder, views):
    for row in views:
        if not row['calibration_passed']:
            continue
        gate = frame_gate(row['report']['measurements'])
        assert gate == row['report']['gate']
        assert row['full_frame_qualified'] == gate['passed']
        path = folder / f'view_{row["index"]}'
        metadata = read(path / 'metadata.json')
        assert sha(path / 'clouds.npz') == metadata['clouds_sha256']
        assert len(metadata['samples']) == REPEATS
        for repeat, sample in enumerate(metadata['samples']):
            assert sample['seed'] == [NOISE_PREFIX, int(folder.name), 0, row['index'], repeat]


def check_state(folder):
    with np.load(folder / 'initial_state.npz') as before, np.load(folder / 'final_state.npz') as after:
        np.testing.assert_array_equal(before['state'], after['state'])
    state = read(folder / 'state_check.json')
    assert state['integration_state_unchanged'] and state['initialization_steps'] == 500
    assert state['task_motion_steps'] == 0 and state['integration_calls_forbidden']


def check_layout(seed):
    folder = RUN / str(seed)
    result = read(folder / 'result.json')
    assert result['seed'] == seed and result['task_motion_attempts'] == 0
    for name, digest in result['evidence'].items():
        assert sha(folder / name) == digest, name
    if result['geometry_accepted']:
        check_state(folder)
        selection = read(folder / 'selection.json')
        assert selection['accepted'] == result['qualified']
        assert len(selection['attempts']) <= 256
    if not result['qualified']:
        return result, {}, []
    fits, views = read(folder / 'fits.json'), read(folder / 'views.json')
    assert len(views) == 5 and views[0]['full_frame_qualified']
    assert fits['selected_pairs'] == [list(p) for p in pairs(views)]
    assert len(fits['singles']) == sum(v['calibration_passed'] for v in views) * REPEATS
    assert len(fits['pairs']) == len(fits['selected_pairs']) * REPEATS
    check_views(folder, views)
    checked = check_fits(folder, fits)
    errors = evaluate.annotate(fits, views, read(folder / 'private_truth.json'))
    assert errors == read(folder / 'private_errors.json')
    assert evaluate.summarize(errors) == result['metrics']
    assert sha(folder / 'fits.json') == result['fits_before_evaluation_sha256']
    return result, errors, checked


def main():
    verify()
    layouts, checks, all_errors = {}, {}, dict(singles=[], pairs=[])
    for seed in SEEDS:
        result, errors, checked = check_layout(seed)
        layouts[str(seed)], checks[str(seed)] = result, checked
        for kind, rows in errors.items():
            all_errors[kind].extend(rows)
    metrics = evaluate.summarize(all_errors)
    qualified = sum(row['qualified'] for row in layouts.values())
    new_false = sum(metrics[k]['all_calibrated']['repair_new_false_accepts'] for k in metrics)
    total_false = sum(metrics[k]['all_calibrated']['selective']['false_accepted'] for k in metrics)
    losses = sum(metrics[k]['all_calibrated']['original_accepted_losses'] for k in metrics)
    assert losses == 0
    result = dict(passed=True, independent_process=True, layouts=layouts, checks=checks,
        qualified_layouts=qualified, registered_layouts=len(SEEDS), metrics=metrics,
        coverage_sufficient=qualified >= 8, repair_new_false_accepts=new_false,
        total_selective_false_accepts=total_false, original_accepted_losses=losses,
        next_control_integration_evidence_gate=qualified >= 8 and new_false == 0 and total_false == 0,
        control_deployed=False, physical_success_rate=None, task_motion_attempts=0,
        model_calls=0, training_runs=0, inputs_unchanged=True)
    verify()
    save(RUN / 'audit.json', result)
    print({k: v for k, v in result.items() if k not in ('layouts', 'checks')}, flush=True)


if __name__ == '__main__':
    main()
