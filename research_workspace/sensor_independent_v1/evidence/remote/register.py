from reflection.__main__ import bootstrap
bootstrap()
import sd_config
import sd_layout
import sd_preflight
import sf_camera
from pose_fresh_v1.register import policy
from camera_joint_v1.register import identities as inherited_identities
from sensor_independent_v1 import worker, audit
from sensor_independent_v1.common import ROOT, PROJECT, RUN, SEEDS, read, save, sha, contains_seed


def isolation():
    patterns = ('*/manifest.json', '*/protocol.json', '*/*/manifest.json',
                'recovery_collection_v1/batches/*/*/manifest.json')
    paths = sorted({p for pattern in patterns for p in PROJECT.glob(pattern) if ROOT not in p.parents})
    hits = [str(p) for p in paths if contains_seed(read(p), SEEDS)]
    assert not hits, hits
    assert not set(SEEDS) & set(range(964001, 965025))
    return dict(patterns=patterns, scanned={str(p): sha(p) for p in paths}, hits=hits)


def identities():
    values = inherited_identities()
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch') or p.name == 'PLAN.md']
    values.update({str(p): sha(p) for p in paths})
    return values


def main():
    RUN.mkdir(exist_ok=False)
    save(RUN / 'registration_started.json', dict(seeds=SEEDS))
    isolated, effective = isolation(), policy()
    assert sf_camera.PIXEL_MARGIN == 24 and sf_camera.IMAGE_SIZE == 640
    geometry = read(PROJECT / 'scene_diversity_v2/manifest.json')['geometry']
    configs, layouts = {}, {}
    for seed in SEEDS:
        layout = sd_layout.sample(seed, geometry)
        config = sd_config.factors(seed, 'combined')
        config.update(group='varied_noisy', bodies=layout['bodies'], geometry_accepted=layout['accepted'],
                      sensor=dict(depth_sigma_m=.003, dropout=.02))
        config['compiled_check'] = (sd_preflight.compiled_check(config, geometry)
                                   if layout['accepted'] else dict(passed=False, reason='layout_rejected'))
        configs[str(seed)], layouts[str(seed)] = config, layout
    save(RUN / 'manifest.json', dict(seeds=SEEDS, seed_isolation=isolated, policy=effective,
        configs=configs, layouts=layouts, identities=identities(), camera_pool_budget=256,
        methods=['original', 'no_msaa'], max_single_clouds=72, max_diagnostic_views=36,
        training_eligible=False, max_task_attempts=0, max_model_calls=0, max_training_runs=0))
    print(dict(registered=len(SEEDS), compiled=sum(c['compiled_check']['passed'] for c in configs.values())), flush=True)


if __name__ == '__main__':
    main()
