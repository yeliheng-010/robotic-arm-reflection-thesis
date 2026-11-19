"""验证闭环与离线噪声来源，冻结全部144项。"""
import json
from loopstudy.protocol import verify as previous_verify
from semanticfix2.protocol import sha
from noisyloop.design import ROOT,items,configuration,MAX_ATTEMPTS


def noise_source():
    root=ROOT.parent/'noise_feedback_v1'
    value=json.loads((root/'protocol.json').read_text())
    assert all(sha(root/name)==digest for name,digest in value['code'].items())
    verified=json.loads((root/'verification.json').read_text())
    assert verified['passed'] and verified['projections']==72
    return dict(protocol_sha256=sha(root/'protocol.json'),code=value['code'])


def manifest():
    files=sorted((ROOT/'noisyloop').glob('*.py'))+[ROOT/'run.sbatch',ROOT/'test_noise_loop.py']
    rows=items()
    assert len(rows)==len({r['id'] for r in rows})==144
    return dict(previous=previous_verify(),noise_source=noise_source(),items=rows,
        scenarios={r['id']:configuration(r) for r in rows},max_attempts=MAX_ATTEMPTS,
        code={str(p):sha(p) for p in files},training_approved=0,test_used=False)


def verify():
    saved=json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(manifest())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(manifest(),stream,ensure_ascii=False,indent=2)
