"""核验旧协议，冻结新增代码、输入及随机顺序。"""
import hashlib
import json
from controlled.freeze import verify as verify_original
from refinement.config import ROOT, PROBES, COLLISION_HEIGHTS, COLLISION_CASES, runs


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def configuration():
    original = verify_original()
    paths = sorted((ROOT/'refinement').glob('*.py')) + sorted(ROOT.glob('*.sbatch'))
    paths += [ROOT/'test_policy.py', ROOT/'diagnostic_inputs.json', ROOT/'environment.sh']
    paths += [ROOT/'diagnostic/result.json', ROOT/'diagnostic/provenance.json']
    source = ROOT.parent/'refinement_v1'
    assert sha(ROOT/'refinement/client.py') == sha(source/'refinement/client.py')
    assert sha(ROOT/'diagnostic/result.json') == sha(source/'diagnostic/result.json')
    assert sha(ROOT/'diagnostic_inputs.json') == sha(source/'diagnostic_inputs.json')
    return dict(code={str(p): sha(p) for p in paths}, original=original,
                smoke=runs('smoke'), regression=runs('regression'), probes=PROBES,
                collision_heights=COLLISION_HEIGHTS, collision_cases=COLLISION_CASES,
                test_used=False, data_role='selected development regression, not held-out efficacy')


def verify():
    stored = json.loads((ROOT/'protocol.json').read_text())
    current = json.loads(json.dumps(configuration()))
    assert stored == current, 'Protocol drift; preserve outputs and create a new version'
    return stored


if __name__ == '__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(configuration(), stream, ensure_ascii=False, indent=2)
    print('Frozen refinement_v3: reuse verified 36 diagnostics; 8 smoke, 96 regression, 12 collision controls')
