"""完整分母、实际机制暴露和来源审计；不自动导出训练数据。"""
import argparse
from copy import deepcopy
from pilot import ROOT,SMOKE_SEEDS,SHARDS,verify,read,save,sha,MAX_PHYSICAL
from audit import audit_scene,audit_trace
from exposure import exposure
from budget_metrics import analyze,failures
from render import write_report


def tamper(values):
    probes=[]
    for mode in ('latest','median'):
        found=False
        for value in values:
            for path in value['trajectories']:
                trace=read(path)
                if trace['mode']==mode and trace['decisions']:
                    probes.append((value,trace))
                    found=True
                    break
            if found:
                break
        assert found,'No auditable decisions for '+mode
    assert len(probes)==2
    rejected=[]
    for value,original in probes:
        q=read(ROOT/'qualification'/value['scene']['id']/'result.json')
        reference=read(q['steps'][0]['result_path'])['records'][0]
        mutations={'physical_hash':lambda t:t['attempts'][0].update(result_sha256='0'*64),
            'observation_state':lambda t:t['decisions'][0]['observation']['samples'][0].update(state={}),
            'visible_truth':lambda t:t['decisions'][0]['feedback']['evidence'].update(hidden_truth=1),
            'budget':lambda t:t.update(extra_observations=99),
            'success':lambda t:t.update(success=not t['success'])}
        for name,mutate in mutations.items():
            changed=deepcopy(original)
            mutate(changed)
            try:
                audit_trace(changed,reference)
            except (AssertionError,ValueError,KeyError):
                rejected.append(dict(method=original['mode'],kind=name))
            else:
                raise AssertionError('Tamper accepted: '+name)
    assert len(rejected)==10,'Incomplete tamper coverage'
    return dict(passed=True,rejections=rejected,count=len(rejected))


def main(phase):
    manifest=verify()
    scenes=[s for s in manifest['scenes'] if phase=='final' or s['seed'] in SMOKE_SEEDS]
    for shard in range(SHARDS):
        stage='smoke' if phase=='smoke' else 'batch'
        assert read(ROOT/'stages'/stage/f'shard_{shard}/progress.json')['status']=='completed'
    values,rows=[],[]
    for scene in scenes:
        path=ROOT/'tasks'/scene['id']
        value=read(path/'result.json')
        assert value['scene']==scene
        checked=audit_scene(value)
        assert checked==read(path/'summary.json')
        values.append(value)
        rows.append(dict(checked,exposure=exposure(value)))
    summary=dict(passed=True,complete=True,expected=len(scenes),accounted=len(rows),
        eligible=sum(r['eligible'] for r in rows),physical_executions=sum(r['physical_executions'] for r in rows),
        physical_budget=sum(MAX_PHYSICAL[s['mechanism']] for s in scenes),
        extra_observations=sum(r['extra_observations'] for r in rows),rows=rows,tamper=tamper(values),
        budget_analysis=analyze(values,read),
        manifest_sha256=sha(ROOT/'manifest.json'),model_calls=0,training_approved=False,test_used=False)
    assert summary['physical_executions']<=summary['physical_budget']
    save(ROOT/f'{phase}_verification.json',summary)
    if phase=='smoke':
        save(ROOT/'gate_smoke.json',dict(passed=True,manifest_sha256=summary['manifest_sha256']))
    save(ROOT/('BUDGET_CURVES.json' if phase=='final' else 'smoke_curves.json'),summary['budget_analysis'])
    save(ROOT/('FAILURES.json' if phase=='final' else 'smoke_failures.json'),failures(values,read))
    write_report(ROOT,summary)
    print({k:v for k,v in summary.items() if k not in ('rows','budget_analysis')},flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('phase',choices=['smoke','final'])
    phase=parser.parse_args().phase
    try:
        main(phase)
    except BaseException as error:
        save(ROOT/f'{phase}_audit_failure.json',dict(passed=False,error=repr(error)))
        raise
