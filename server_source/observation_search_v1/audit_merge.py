from reflection.__main__ import bootstrap
bootstrap()
from pose_fresh_v1.evaluate import summarize
from sensor_independent_v1 import assessment
from observation_search_v1.common import RUN, METHODS, SEEDS, read, save, sha, verify


def audited(seed):
    path = RUN / ('first_audit.json' if seed == SEEDS[0] else f'audit_part_{seed}.json')
    part = read(path)
    assert part['passed'] and part['seed'] == seed
    if seed != SEEDS[0]:
        started = read(RUN / f'audit_started_{seed}.json')
        assert started['manifest_sha256'] == sha(RUN / 'manifest.json')
        for name, digest in started['sources'].items():
            assert sha(name) == digest, name
    result, folder = part['result'], RUN / str(seed)
    original = read(folder / 'result.json')
    assert all(result[k] == v for k, v in original.items())
    for name, digest in result['evidence'].items():
        assert sha(folder / name) == digest, name
    rays = [r for i in result.get('diagnostic_indices', [])
            for r in read(folder / f'pair_{i}/reference.json')['rays']]
    assert len(rays) == part['ray_count']
    if rays:
        assert assessment.ray_metrics(rays) == result['ray_statistics']
    return result, part['pose_errors'], part['checks'], rays


def main():
    manifest = verify()
    layouts, checks, all_rays = {}, {}, []
    combined = {method: dict(singles=[], pairs=[]) for method in METHODS}
    for seed in SEEDS:
        result, errors, checked, rays = audited(seed)
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
