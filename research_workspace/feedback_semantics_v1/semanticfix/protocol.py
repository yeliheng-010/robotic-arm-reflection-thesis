"""新目录独立冻结，不修改原物理实验。"""
import hashlib
import json
from recovery.protocol import verify as previous_verify
from recovery.references import BASE
from semanticfix.design import items,configuration

ROOT = BASE/'feedback_semantics_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    files = sorted((ROOT/'semanticfix').glob('*.py'))+sorted(ROOT.glob('*.sbatch'))+[ROOT/'test_semantics.py']
    return dict(previous=previous_verify(),items=items(),scenarios={r['id']:configuration(r) for r in items()},
                code={str(p):sha(p) for p in files},test_used=False,training_approved=0)


def verify():
    saved = json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(manifest())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(manifest(),stream,ensure_ascii=False,indent=2)
