"""只读核验旧协议；独立冻结新脚本、合成输入与实验清单。"""
import hashlib
import json
from pathlib import Path
from refinement.freeze import verify as verify_previous
from nextstudy.design import physical_items
from nextstudy.fixtures import fixtures

ROOT = Path('/home/yeliheng/grasp_server/refinement_next_v1')
REVIEW = ROOT.parent/'refinement_review_v1/review_data.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configuration():
    previous = verify_previous()
    data = json.loads(REVIEW.read_text())
    run = next(r for r in data['runs'] if r['id']=='07_flash_new_0')
    residual = run['feedback'][0]['projected']['evidence']['grasp_residual_xy']
    paths = sorted((ROOT/'nextstudy').glob('*.py'))+sorted(ROOT.glob('*.sbatch'))
    paths += [ROOT/'test_nextstudy.py']
    source = {str(REVIEW):sha(REVIEW)}
    for case in (7,25,37,47):
        old = next(r for r in data['runs'] if r['id']==f'{case:02d}_flash_new_0')
        for path, digest in old['source_files'].items():
            assert sha(Path(path)) == digest, 'Source experiment changed'
            source[path] = digest
    return dict(code={str(p):sha(p) for p in paths}, previous=previous,
                source=source, physical=physical_items(residual),
                fixtures=fixtures(), test_used=False, data_role='development_diagnostics',
                semantic_calls=96, repetitions=3, order_seed=20261024)


def freeze():
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(configuration(), stream, ensure_ascii=False, indent=2)


def verify():
    stored = json.loads((ROOT/'protocol.json').read_text())
    assert stored == json.loads(json.dumps(configuration())), 'Frozen protocol drift'
    return stored


if __name__ == '__main__':
    freeze()
