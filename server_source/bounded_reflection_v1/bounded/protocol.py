"""冻结混合方法代码和用例；原协议与能力探针作为只读依据。"""
import hashlib
import json
from pathlib import Path
from nextstudy.protocol import verify as previous_verify
from nextstudy.fixtures import fixtures

ROOT = Path('/home/yeliheng/grasp_server/bounded_reflection_v1')
CASES = (7,25,31,37,42,47)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def runs():
    return [dict(case=case,arm=arm,repeat=repeat,id=f'{case:02d}_{arm}_{repeat}')
            for case in CASES for arm in ('retry','priority','random','hybrid')
            for repeat in range(2 if arm=='hybrid' else 1)]


def configuration():
    previous = previous_verify()
    paths = sorted((ROOT/'bounded').glob('*.py'))+sorted(ROOT.glob('*.sbatch'))
    paths += [ROOT/'test_contract.py',ROOT/'probe_api.py',ROOT/'capability/result.json']
    return dict(previous=previous,code={str(p):sha(p) for p in paths},fixtures=fixtures(),
                semantic_calls=96,semantic_seed=904250,closed_loop=runs(),test_used=False,
                method='rule_generated_candidates_llm_selection_template_explanation',
                schema_is_hard_constraint=False)


def verify():
    saved = json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(configuration())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(configuration(),stream,ensure_ascii=False,indent=2)
