"""冻结预登记布局与代码，测试几何拒绝和结果篡改检测。"""
import copy
import sys
import numpy as np
from pathlib import Path
from cl_common import read, save, sha
from cl_design import ROOT, SCENE, SEEDS, SMOKE_SEEDS, items, sampled_layout, CONTAINERS
from cl_geometry import inventory, check_positions, verify_compiled
from cl_worker import audit_row
from cl_sampling import valid_candidates


def checks(geometry, layouts):
    assert len(items())==160 and len({r['id'] for r in items()})==160
    assert all(value==sampled_layout(int(seed), geometry) for seed,value in layouts.items())
    assert all(v['accepted'] for v in layouts.values()), 'Sampling design infeasible before execution'
    positions = copy.deepcopy(layouts[str(SEEDS[0])]['positions'])
    positions[CONTAINERS[0]] = [-1., -1.]
    assert not check_positions(positions, geometry, require_move=True)['passed']
    positions[CONTAINERS[0]] = positions[CONTAINERS[1]]
    assert not check_positions(positions, geometry, require_move=True)['passed']
    original = {n: geometry['centers'][n][:2] for n in CONTAINERS}
    assert not check_positions(original, geometry, require_move=True)['passed']
    assert check_positions(original, geometry, require_move=False)['passed']
    rng=np.random.default_rng(123)
    batch=rng.uniform((.85,.15),(1.44,1.05),(128,3,2))
    expected=[check_positions(dict(zip(CONTAINERS,b.tolist())),geometry,require_move=True)['passed'] for b in batch]
    np.testing.assert_array_equal(expected,valid_candidates(batch,geometry))
    accepted=np.array([list(v['positions'].values()) for v in layouts.values()])
    assert valid_candidates(accepted,geometry).all()


def registered_sources():
    from pilot import extract_seeds
    sources=set(ROOT.parent.glob('*/protocol.json')) | set(ROOT.parent.glob('*/manifest.json'))
    sources.discard(ROOT/'manifest.json')
    used=set()
    for path in sources:
        used.update(extract_seeds(read(path)))
    assert not set(SEEDS)&used, 'Registered seed overlap'
    return sources


def freeze():
    assert not (ROOT/'manifest.json').exists(), 'Never overwrite a frozen run'
    from expand.protocol import verify as verify_parent
    verify_parent()
    sources=registered_sources()
    geometry = inventory()
    layouts = {}
    for seed in SEEDS:
        layouts[str(seed)]=sampled_layout(seed,geometry)
        save(ROOT/'sampling_progress.json',layouts)
        print(seed,layouts[str(seed)]['accepted'],layouts[str(seed)]['rejected'],flush=True)
    checks(geometry, layouts)
    plan = dict(items=items(), layouts=layouts, geometry=geometry,
        smoke_seeds=SMOKE_SEEDS, test_used=False, training_approved=False)
    for item in items():
        assert verify_compiled(item, layouts[str(item['seed'])], geometry)['checks']['passed']
    save(ROOT/'plan.json', plan)
    files = set(ROOT.glob('*.py')) | set(ROOT.glob('*.sbatch')) | set(ROOT.glob('*.sh')) | {ROOT/'PROTOCOL.md'}
    for module in list(sys.modules.values()):
        path = getattr(module, '__file__', None)
        if path and '/grasp_server/' in path and '/env_' not in path and path.endswith('.py'):
            files.add(Path(path))
    files.update(SCENE.parent.parent.rglob('*.xml'))
    files.update((ROOT.parent/'improvement_20261019/code').rglob('*.py'))
    files.update(sources)
    for folder in ('scene_expansion_v1', 'route_loop_v1', 'descent_route_v1', 'descent_pose_v2',
                   'feedback_semantics_v2', 'recovery_study_v1', 'diversity_v1', 'controlled_v3'):
        files.update((ROOT.parent/folder).rglob('*.py'))
    save(ROOT/'manifest.json', dict(identities={str(p):sha(p) for p in sorted(files)},
        plan_sha256=sha(ROOT/'plan.json'), test_used=False, training_approved=False))
    save(ROOT/'preflight.json', dict(passed=True, conditions=160, seeds=40,
        compiled_checks=160, checks=['determinism','unique_ids','outside_table_rejected',
        'overlap_rejected','unchanged_layout_rejected','baseline_valid','all_three_coordinates_applied']))
    print('PREFLIGHT PASS: 40 layouts, 160 compiled conditions')


if __name__=='__main__':
    freeze()
