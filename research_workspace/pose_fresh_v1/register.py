"""独立种子扫描、配置编译和执行源码冻结。"""
import sys
from pathlib import Path
from reflection.__main__ import bootstrap
bootstrap()
import cv_policy
import cv_select
import sd_config
import sd_layout
import sd_preflight
import sd_render
import sf_camera
from pose_fresh_v1 import worker
from pose_fresh_v1.policy import SEEDS
from pose_fresh_v1.common import ROOT, PROJECT, RUN, read, save, sha, contains_seed


def isolation():
    patterns = ('*/manifest.json', '*/protocol.json', '*/*/manifest.json',
                'recovery_collection_v1/batches/*/*/manifest.json')
    paths = sorted({p for pattern in patterns for p in PROJECT.glob(pattern)
                    if ROOT not in p.parents})
    hits = [str(p) for p in paths if contains_seed(read(p), SEEDS)]
    assert not hits, hits
    assert not set(SEEDS) & set(range(964001, 965025))
    return dict(patterns=patterns, scanned={str(p): sha(p) for p in paths}, hits=hits,
                scope='listed manifest/protocol patterns, not exhaustive all-file scan')


def identities():
    paths = set(ROOT.glob('*.py')) | set(ROOT.glob('*.sbatch')) | {ROOT / 'PLAN.md'}
    paths.add(PROJECT / 'scene_diversity_v2/manifest.json')
    paths.update(PROJECT.glob('*/environment.sh'))
    paths.update(PROJECT.glob('*/*/environment.sh'))
    for module in tuple(sys.modules.values()):
        path = Path(getattr(module, '__file__', '') or '')
        if PROJECT in path.parents and path.suffix == '.py' and not {'env_sim', 'qwen35'} & set(path.parts):
            paths.add(path)
    return {str(p): sha(p) for p in sorted(paths)}


def policy():
    assert Path(cv_policy.__file__).parent.name == 'camera_visibility_v6'
    assert len(cv_policy.REQUIRED) == 14 and len(sd_config.MOVING) == 7
    assert cv_policy.MIN_FRACTION == .85 and cv_policy.MIN_PIXELS == 576
    assert cv_policy.MIN_SHORT_SIDE == 16 and cv_policy.MIN_COMPONENT_FRACTION == .8
    assert cv_policy.SLENDER_MIN_PIXELS == 256 and cv_policy.SLENDER_MIN_SHORT_SIDE == 12
    assert cv_policy.SLENDER_MIN_LONG_SIDE == 24 and sd_render.DEPTH_TOLERANCE == .006
    assert cv_select.SETTLE_STEPS == 500
    return dict(module=cv_policy.__file__, required=cv_policy.REQUIRED, min_fraction=.85,
                ordinary_pixels=576, ordinary_short_side=16, connected=.8,
                slender_pixels=256, slender_short_side=12, slender_long_side=24,
                depth_tolerance_m=.006, camera_module=sf_camera.__file__)


def main():
    RUN.mkdir(exist_ok=False)
    save(RUN / 'registration_started.json', dict(seeds=SEEDS))
    isolated, effective = isolation(), policy()
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
        configs=configs, layouts=layouts, identities=identities(), max_single_clouds=180,
        max_pairs=108, max_task_attempts=0, max_model_calls=0, training_eligible=False))
    print(dict(registered=len(SEEDS), compiled=sum(c['compiled_check']['passed'] for c in configs.values())), flush=True)


if __name__ == '__main__':
    main()
