"""冻结新协议并验证整个上游协议链。"""
import json
from routecheck.protocol import verify as previous_verify
from semanticfix2.protocol import sha
from loopstudy.design import ROOT,items,configuration,MAX_ATTEMPTS


def manifest():
    files = sorted((ROOT/'loopstudy').glob('*.py'))+[ROOT/'run.sbatch',ROOT/'test_loop.py']
    return dict(previous=previous_verify(),items=items(),scenarios={r['id']:configuration(r) for r in items()},
                code={str(p):sha(p) for p in files},max_attempts=MAX_ATTEMPTS,training_approved=0,test_used=False)


def verify():
    saved = json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(manifest())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(manifest(),stream,ensure_ascii=False,indent=2)
