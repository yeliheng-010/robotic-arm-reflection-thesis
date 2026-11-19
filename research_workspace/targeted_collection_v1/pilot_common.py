"""新训练种子、有限采样预算与独立冻结身份。"""
import json
from pathlib import Path
from unittest.mock import patch
from common import verify as verify_parent, sha, read, save
from hardstudy import design

ROOT = Path('/home/yeliheng/grasp_server/targeted_collection_v1')
SEEDS = tuple(range(930001, 930007))
FAMILIES = ('grasp_collision', 'grasp_place')
MAX_PHYSICAL = 10
SHARDS = 4


def scenes():
    with patch.object(design, 'SEEDS', SEEDS), patch.object(design, 'TRAIN_SEED_COUNT', len(SEEDS)):
        rows = [s for s in design.scenes() if s['factor'] in FAMILIES]
    for row in rows:
        key = 'T' + row['id'][1:]
        row.update(id=key, scene_id=key, pair_id=key)
    return rows


def source_seeds():
    used = set()
    for folder in ('noisy_loop_v1', 'scene_expansion_v1', 'hard_cases_v1'):
        protocol = read(ROOT.parent / folder / 'protocol.json')
        used.update(row['seed'] for row in protocol['items'])
        used.update(protocol.get('reserved_test_seeds', []))
    return used


def freeze():
    verify_parent()
    assert not set(SEEDS) & source_seeds()
    rows = scenes()
    assert len(rows) == 24 and all(r['split'] == 'train_candidate' for r in rows)
    files = sorted(ROOT.glob('*.py')) + sorted(ROOT.glob('*.sbatch')) + [ROOT/'environment.sh']
    value = dict(scenes=rows, seeds=SEEDS, max_attempts=3, alternatives_per_node=2,
        max_physical_per_scene=MAX_PHYSICAL, total_physical_budget=len(rows)*MAX_PHYSICAL,
        model=None, source='expert_counterfactual_rule_continuation', test_used=False,
        parent_manifest=sha(ROOT.parent/'candidate_closed_loop_v2/manifest.json'),
        data_manifest=sha(ROOT.parent/'data_review_v1/output_v1/manifest.json'),
        code={str(p): sha(p) for p in files})
    with (ROOT/'manifest.json').open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
    return value


def verify():
    verify_parent()
    value = read(ROOT/'manifest.json')
    assert value['parent_manifest'] == sha(ROOT.parent/'candidate_closed_loop_v2/manifest.json')
    assert value['data_manifest'] == sha(ROOT.parent/'data_review_v1/output_v1/manifest.json')
    assert all(sha(Path(p)) == digest for p, digest in value['code'].items())
    assert value['scenes'] == scenes() and not set(SEEDS) & source_seeds()
    assert value['total_physical_budget'] == 240 and value['model'] is None
    return value


if __name__ == '__main__':
    print({'scenes': len(freeze()['scenes']), 'max_physical': 240})
