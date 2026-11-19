"""复核96轨迹并解析45次模型决策，源数据只读。"""
from pathlib import Path
from om_common import ROOT as SOURCE,read,save,sha,verify
from om_audit import audit_scene
from om_metrics import analyze as curves
from core import feature,summarize

ROOT=SOURCE.parent/'selector_analysis_v1'


def snapshot(manifest):
    paths=set(SOURCE.rglob('*.json'))|{Path(p) for p in manifest['identities']}
    return {str(p):sha(p) for p in sorted(paths)}


def decisions(values):
    output=[]
    for value in values:
        traces={p.split('/')[-2]:read(p) for p in value['trajectories']}
        for aggregation in ('latest','median'):
            if not traces:
                continue
            a,b=(traces[p+'_'+aggregation] for p in ('base','rule'))
            assert len(a['decisions'])==len(b['decisions'])
            for i,(model,rule) in enumerate(zip(a['decisions'],b['decisions'])):
                output.append(dict(id=value['scene']['id'],aggregation=aggregation,after_attempt=i+1,
                    model_selected=model['selected'],rule_selected=rule['selected'],
                    **feature(model,rule,next_success=a['attempts'][i+1]['success'])))
    return output


def main():
    assert not (ROOT/'summary.json').exists()
    manifest=verify()
    before=snapshot(manifest)
    values=[]
    for scene in manifest['scenes']:
        directory=SOURCE/'tasks'/scene['id']
        value=read(directory/'result.json')
        assert value['scene']==scene and audit_scene(value)==read(directory/'summary.json')
        values.append(value)
    prior=read(SOURCE/'verification.json')
    assert prior['passed'] and prior['complete']
    assert curves(values,read)==prior['budget_analysis']
    rows=decisions(values)
    assert len(rows)==prior['model_calls']==45
    assert snapshot(manifest)==before
    summary=dict(passed=True,reaudited_conditions=24,trajectories=96,source_files_unchanged=len(before),
        totals=summarize(rows),by_aggregation={m:summarize([r for r in rows if r['aggregation']==m])
            for m in ('latest','median')},new_physical_executions=0,new_model_calls=0,test_used=False,
        source_manifest_sha256=sha(SOURCE/'manifest.json'),post_hoc=True,
        code={str(p):sha(p) for p in ROOT.glob('*.py')})
    save(ROOT/'decisions.json',rows)
    save(ROOT/'source_hashes.json',before)
    save(ROOT/'summary.json',summary)
    print(summary,flush=True)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json',dict(error=repr(error),passed=False))
        raise
