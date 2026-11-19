"""复用最终物理审计，来源文件分析前后均hash核验。"""
from collections import Counter,defaultdict
from pathlib import Path
from common import ROOT as SOURCE,read,save,sha,verify
from report import load
from loopstudy.actions import initial,choose_rule
from core import compare_pair,features,aggregate,feedback_context,history_opportunities
from render import write_report

ROOT=SOURCE.parent/'framework_analysis_v1'


def snapshot(entries):
    paths={SOURCE/'manifest.json',SOURCE/'verification.json'}
    paths.update(Path(p) for p in read(SOURCE/'manifest.json')['identities'])
    for e in entries:
        folder=SOURCE/'tasks'/e['uid']
        paths.update([folder/'result.json',folder/'summary.json'])
        result=read(folder/'result.json')
        paths.update(Path(s['result_path']) for s in result['attempts'])
        paths.update(SOURCE/'service/requests'/f"{d['event']['response']['id']}.json"
                     for d in result['decisions'] if 'event' in d)
    return {str(p):sha(p) for p in sorted(paths)}


def compact(result):
    return dict(success=result['success'],attempts=[dict(index=s['index'],success=s['success'],
        state=s['state'],**feedback_context(s['feedback'])) for s in result['attempts']],
        decisions=[dict(after_attempt=d['after_attempt'],selected=d['selected'],
                        candidate_kinds=[c['kind'] for c in d['candidates']]) for d in result['decisions']])


def grouped_comparison(groups):
    totals={3:Counter(),4:Counter()}
    differences,failures=[],[]
    for (budget,scene),methods in groups.items():
        comparison=compare_pair(methods['current'],methods['history'])
        totals[budget].update(comparison['counts'])
        if comparison['differences']:
            differences.append(dict(budget=budget,scene=scene,**comparison))
        if not methods['history']['success']:
            failures.append(dict(budget=budget,scene=scene,rule_only_success=methods['rule']['success'],
                                 methods={m:compact(r) for m,r in methods.items()}))
    return dict(totals={str(b):dict(c) for b,c in totals.items()},differences=differences,failures=failures)


def feature_rows(pairs):
    output=[]
    for entry,result in pairs:
        if entry['method'] not in ('history','current'):
            continue
        for index,d in enumerate(result['decisions']):
            rule=choose_rule(d['candidates'],d['before'],report=d['feedback']) if d['candidates'] else None
            output.append(dict(budget=entry['max_attempts'],method=entry['method'],scene=entry['item']['scene_id'],
                **features(result,index,initial_state=initial(),rule_choice=rule)))
    return output


def main():
    assert not (ROOT/'summary.json').exists(),'Preserve existing analysis'
    manifest=verify()
    prior=read(SOURCE/'verification.json')
    assert prior['passed'] and prior['complete'] and prior['accounted']==480
    before=snapshot(manifest['entries'])
    save(ROOT/'source_hashes.json',before)
    rows,pairs=load(manifest['entries'])
    assert len(rows)==len(pairs)==480
    groups=defaultdict(dict)
    for e,result in pairs:
        groups[(e['max_attempts'],e['item']['scene_id'])][e['method']]=result
    comparison=grouped_comparison(groups)
    details=feature_rows(pairs)
    buckets={f'b{b}_{m}':aggregate([r for r in details if r['budget']==b and r['method']==m])
             for b in (3,4) for m in ('current','history')}
    records=[(e['uid']+f':{i+1}',d) for e,r in pairs if e['max_attempts']==4 and e['method']=='history'
             for i,d in enumerate(r['decisions'])]
    for path,value in before.items():
        assert sha(path)==value,'Source changed: '+path
    summary=dict(passed=True,reaudited_tasks=480,source_files_unchanged=len(before),
        source_manifest_sha256=sha(SOURCE/'manifest.json'),analysis_code={str(p):sha(p) for p in ROOT.glob('*.py')},
        comparison_totals=comparison['totals'],features=buckets,opportunities=history_opportunities(records),
        new_physical_executions=0,new_model_calls=0,new_training_inputs=0,test_used=False)
    save(ROOT/'decisions.json',details)
    save(ROOT/'cases.json',comparison)
    save(ROOT/'summary.json',summary)
    write_report(ROOT,summary,comparison)
    print(summary,flush=True)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json',dict(passed=False,error=repr(error)))
        raise
