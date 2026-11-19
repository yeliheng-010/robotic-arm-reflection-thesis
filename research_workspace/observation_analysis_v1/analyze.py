"""重审物理结果并核验来源不变；无模型调用或物理执行。"""
from collections import Counter
from pathlib import Path
from pilot import ROOT as SOURCE,verify,read,save,sha
from audit import audit_scene
from budget_metrics import analyze as budgets
from oa_metrics import condition
from oa_render import render

ROOT=SOURCE.parent/'observation_analysis_v1'


def snapshot(manifest):
    paths=set(SOURCE.rglob('*.json'))|{Path(p) for p in manifest['identities']}
    paths.add(SOURCE/'REPORT.md')
    return {str(p):sha(p) for p in sorted(paths)}


def statistics(rows):
    metrics=[]
    gaps=[]
    for row in rows:
        initial=row['initial']
        if initial is None:
            continue
        used=set(initial['consumed_fields'].values())-{None}
        for field in initial['fields']:
            if field['field'] in used:
                metrics.append(field)
        if used and initial['heuristic_target'] not in used:
            gaps.append(row['id'])
    changed=[r['id'] for r in rows if any(b['paired'] in ('latest_only','median_only') for b in r['budgets'])]
    return dict(conditions=len(rows),seed_groups=len({r['seed'] for r in rows}),
        initial_decisions=sum(r['initial'] is not None for r in rows),
        consumed_field_comparisons=len(metrics),error_directions=dict(Counter(m['error_direction'] for m in metrics)),
        consumed_last_outlier=sum(m['last_sample_outlier'] for m in metrics),
        heuristic_misses=gaps,different_outcome_conditions=changed)


def main():
    assert not (ROOT/'summary.json').exists(),'Existing analysis must be preserved'
    manifest=verify()
    prior=read(SOURCE/'final_verification.json')
    assert prior['passed'] and prior['complete'] and prior['accounted']==24
    before=snapshot(manifest)
    code={str(p):sha(p) for p in ROOT.glob('*.py')}
    values=[]
    for scene in manifest['scenes']:
        folder=SOURCE/'tasks'/scene['id']
        value=read(folder/'result.json')
        assert value['scene']==scene
        assert audit_scene(value)==read(folder/'summary.json')
        values.append(value)
    assert budgets(values,read)==prior['budget_analysis']
    rows=[condition(v,read) for v in values]
    assert snapshot(manifest)==before,'Source files changed during analysis'
    assert all(sha(p)==h for p,h in code.items())
    summary=dict(passed=True,reaudited_conditions=len(rows),source_files_unchanged=len(before),
        source_manifest_sha256=sha(SOURCE/'manifest.json'),analysis_code=code,
        statistics=statistics(rows),post_hoc=True,new_physical_executions=0,new_model_calls=0,
        new_training_inputs=0,test_used=False)
    save(ROOT/'source_hashes.json',before)
    save(ROOT/'cases.json',rows)
    render(ROOT,summary,rows)
    save(ROOT/'summary.json',summary)
    print(summary,flush=True)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json',dict(passed=False,error=repr(error)))
        raise
