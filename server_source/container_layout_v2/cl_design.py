"""独立容器布局资格实验；不依据物理成功结果重抽样。"""
from pathlib import Path
import numpy as np
from controlled.config import scenario
from stability.collection_plan import HELDOUT

ROOT = Path('/home/yeliheng/grasp_server/container_layout_v2')
SCENE = ROOT.parent/'improvement_20261019/code/manipulator_grasp/assets/scenes/scene.xml'
SEEDS = tuple(range(950401, 950441))
PAIRS = (('RedBlock', 'BlueBin'), ('PurpleCapsule', 'RedBin'))
CONTAINERS = ('BlueBin', 'RedBin', 'SortingTray')
ARMS = ('original', 'randomized')
SHARDS = 4
SMOKE_SEEDS = SEEDS[:2]
XY_LOW, XY_HIGH = (.85, .15), (1.44, 1.05)
CLEARANCE = .008
MIN_MOVE = .06
MAX_LAYOUT_TRIES = 262144
SAMPLE_BATCH = 1024
WORKER_SECONDS = 900


def items():
    rows = []
    for seed in SEEDS:
        for pair, (source, destination) in enumerate(PAIRS):
            assert HELDOUT.get((source, destination)) != 'test'
            for arm in ARMS:
                rows.append(dict(id=f'L{pair}_{seed}_{arm}', source=source,
                    destination=destination, seed=seed, arm=arm,
                    split='development_qualification', fault='none'))
    return rows


def configuration(item, layout):
    config = scenario(item['seed'], 'clean')
    config.update(version='container-layout-v2', level=item['arm'])
    config['containers'] = layout['offsets'] if item['arm'] == 'randomized' else {
        name: [0., 0.] for name in CONTAINERS}
    return config


def sampled_layout(seed, geometry):
    from cl_geometry import check_positions
    from cl_sampling import valid_candidates
    rng = np.random.default_rng(np.random.SeedSequence([seed, 950400]))
    for start in range(0, MAX_LAYOUT_TRIES, SAMPLE_BATCH):
        batch = rng.uniform(XY_LOW, XY_HIGH, (SAMPLE_BATCH, 3, 2))
        valid = np.flatnonzero(valid_candidates(batch, geometry))
        if len(valid):
            chosen=int(valid[0])
            positions=dict(zip(CONTAINERS,batch[chosen].tolist()))
            checks=check_positions(positions,geometry,require_move=True)
            assert checks['passed'], 'Vector/scalar geometry disagreement'
            offsets = {n: (np.array(positions[n])-geometry['centers'][n][:2]).tolist()
                       for n in CONTAINERS}
            return dict(seed=seed, accepted=True, positions=positions, offsets=offsets,
                        rejected=start+chosen, checks=checks)
    positions=dict(zip(CONTAINERS,batch[-1].tolist()))
    checks=check_positions(positions,geometry,require_move=True)
    return dict(seed=seed, accepted=False, positions=positions, offsets={},
                rejected=MAX_LAYOUT_TRIES, checks=checks)
