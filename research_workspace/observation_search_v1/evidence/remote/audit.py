from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.audit import check_state, check_fits
from pose_fresh_v1.evaluate import annotate, summarize
from sensor_independent_v1 import assessment, audit_arrays
from observation_search_v1 import audit_data, search
from observation_search_v1.common import RUN, METHODS, SEEDS, NOISE_PREFIX, read, save, sha, verify


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
    boxes = read(folder / 'boxes.json')
    observations = audit_data.check_observations(folder, boxes)
    searches = audit_data.check_searches(folder, observations, config=config, boxes=boxes)
    measured = [r['index'] for r in observations if 'rgb' in r]
    assert len(measured) == result['measured'] and measured[:3] == result['diagnostic_indices']
    errors, checks, counts = {}, {}, {}
    for method in METHODS:
        rows = search.hydrated(searches[method], observations)
        accepted = [r['index'] for r in rows if r['accepted']]
        counts[method] = dict(candidates=len(rows), measured=sum('rgb' in r for r in rows),
            geometric=sum(r.get('geometry_accepted', False) for r in rows), usable=len(accepted))
        assert bool(accepted) == (method in result['accepted'])
        if accepted:
            assert accepted[0] == result['accepted'][method]['index']
            errors[method], checks[method] = check_pose(folder / method, result['accepted'][method], seed)
    rays = audit_arrays.check_layout(folder, config, result['diagnostic_indices'])
    result.update(search_statistics=counts, rgb_statistics=audit_data.rgb_statistics(observations),
                  ray_statistics=assessment.ray_metrics(rays))
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
    gained = sorted(set(qualified['adaptive']) - set(qualified['joint']))
    lost = sorted(set(qualified['joint']) - set(qualified['adaptive']))
    valid = [r for r in layouts.values() if r.get('diagnostic_indices')]
    coverage = len(valid) >= 8 and sum(len(r['diagnostic_indices']) for r in valid) >= 24
    rays_ok = all(assessment.ray_nonregression(r['ray_statistics']) for r in valid)
    false = metrics['adaptive']['singles']['qualified']['selective']['false_accepted']
    rgb = {key: sum(r['rgb_statistics'][key] for r in valid) for key in valid[0]['rgb_statistics']} if valid else {}
    verify()
    result = dict(passed=True, independent_process=True, layouts=layouts, checks=checks,
        qualified=qualified, gained=gained, lost=lost, metrics=metrics, rgb_statistics=rgb,
        diagnostic_coverage_sufficient=coverage, ray_nonregression=rays_ok,
        ray_statistics=assessment.ray_metrics(all_rays),
        next_integration_gate=coverage and len(qualified['adaptive']) >= 8 and not lost and false == 0
            and rays_ok and rgb.get('stability_failures', 1) == 0 and rgb.get('post_failures', 1) == 0,
        control_deployed=False, task_motion_attempts=0, model_calls=0, training_runs=0, inputs_unchanged=True)
    save(RUN / 'audit.json', result)
    print({k: v for k, v in result.items() if k not in ('layouts', 'checks', 'metrics')}, flush=True)


if __name__ == '__main__':
    main()
