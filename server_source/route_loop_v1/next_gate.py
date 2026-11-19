"""以完整审计结果决定能否进入带噪声闭环阶段。"""
import importlib.util
import json
from pathlib import Path
import sys
from loopstudy.protocol import verify
from loopstudy.design import ROOT,ARMS
from stability.collection_status import atomic


def read(name):
    return json.loads((ROOT/name).read_text())


def noise_check():
    directory=ROOT.parent/'noise_feedback_v1'
    sys.path.insert(0,str(directory))
    spec=importlib.util.spec_from_file_location('noise_preflight',directory/'run.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    protocol=json.loads((directory/'protocol.json').read_text())
    assert protocol==json.loads(json.dumps(module.manifest()))
    saved=json.loads((directory/'result.json').read_text())
    rows=[module.check_one(f,p,s) for f in protocol['fixtures'] for p in protocol['profiles'] for s in protocol['seeds']]
    assert len(rows)==72 and rows==saved['rows'] and saved['summary']['passed']
    return dict(projections=72,model_calls=0,physical_runs=0,passed=True)


if __name__=='__main__':
    verify()
    physical,comparison,model=read('verification.json'),read('comparison.json'),read('model_review.json')
    assert physical['completed']==physical['expected']==24
    totals=[r for r in physical['metrics'] if r['group']=='all']
    assert {r['arm'] for r in totals}==set(ARMS) and all(r['n']==6 for r in totals)
    assert sum(r['attempts'] for r in totals)<=72
    assert not any(r['invalid'] or r['service_errors'] for r in totals)
    assert comparison['passed'] and comparison['tasks']==24 and model['valid']==model['calls']
    assert all(r['audit']['passed'] for r in physical['rows'])
    assert next(r['successes'] for r in physical['metrics'] if r['group']=='anchor' and r['arm']=='new_rule')==2
    output=dict(status='ready',next_stage='paired_noisy_feedback_closed_loop',tasks=24,
        physical_attempts=sum(r['attempts'] for r in totals),noise_preflight=noise_check(),
        training_approved=0,model_advantage_demonstrated=False,
        scope='development integration gate; not final test or noisy physical validation')
    atomic(ROOT/'next_gate.json',output)
    print(json.dumps(output))
