"""只读引用最终保护版本的九条证据，不改原结果。"""
from pathlib import Path
from sd_common import read, sha
from route_policy import eligible

ROOT = Path(__file__).resolve().parent
PREVIOUS = ROOT.parent/'scene_pair_guard_v2'


def inputs():
    manifest = read(PREVIOUS/'manifest.json')
    verification = read(PREVIOUS/'verification.json')
    assert verification['passed'] and verification['preserved_successes'] == 7
    cases = []
    for row in verification['rows']:
        if row['id'].endswith('release_only'):
            continue
        case = next(c for c in manifest['cases'] if c['id'] == row['id'])
        root = Path(row['evidence_root'])
        step = read(root/'audit.json')['step']
        assert sha(step['result_path']) == step['result_sha256']
        assert step['index'] == 1
        assert step['success'] or eligible(step['feedback'], case['item']['destination'])
        cases.append(dict(id=case['id'], item=case['item'], config=case['config'],
                          first=step, evidence_root=str(root), reused_success=step['success']))
    assert len(cases) == 9 and sum(c['reused_success'] for c in cases) == 7
    return cases
