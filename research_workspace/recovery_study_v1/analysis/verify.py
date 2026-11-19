"""重审完整分母、原始动作和反馈不干预物理的阴性对照。"""
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path('/home/yeliheng/grasp_server/recovery_study_v1')
sys.path.insert(0,str(ROOT))
from recovery.protocol import verify,sha
from recovery.audit import audit
from controlled.worker import jsonlines
from stability.collection_status import atomic


def trajectory(result,directory):
    feedback = {e['attempt']:e for e in jsonlines(directory/'feedback.jsonl')}
    rows = []
    for record in result['records']:
        shown = feedback.get(record['attempt'],{}).get('projected',{}).get('evidence',{})
        error = record.get('error') or {}
        rows.append(dict(attempt=record['attempt'],accepted=record['accepted'],error=error.get('error_type'),
                         segment=record.get('diagnostics',{}).get('motion_segment'),
                         parameters=record['parameters'],changes=record.get('reflection',{}).get('changes'),
                         reflection_source=record.get('reflection',{}).get('source'),
                         shown_grasp_residual=shown.get('grasp_residual_xy'),
                         raw_grasp_residual=error.get('evidence',{}).get('grasp_residual_xy')))
    return rows


def row(item):
    directory = ROOT/'tasks'/item['id']
    result = json.loads((directory/'result.json').read_text())
    verified = audit(directory,result,item)
    saved = json.loads((directory/'summary.json').read_text())
    assert saved['audit']==verified and saved['success']==result['success']
    assert saved['attempts']==result['attempts']
    return dict(item=item,success=result['success'],attempts=result['attempts'],audit=verified,
                result_sha256=sha(directory/'result.json'),trajectory=trajectory(result,directory))


def negative_controls(items,rows):
    finished = {r['item']['id'] for r in rows}
    checked = []
    for arm in ('retry','candidate_depth','depth_candidate'):
        group = [r for r in items if r['study']=='feedback' and r['arm']==arm]
        if not all(r['id'] in finished for r in group):
            continue
        results = [json.loads((ROOT/'tasks'/r['id']/'result.json').read_text()) for r in group]
        reference = results[0]
        for other in results[1:]:
            assert reference['success']==other['success'] and reference['attempts']==other['attempts']
            for first,second in zip(reference['records'],other['records']):
                for key in ('parameters','accepted','physical_success','domain_randomization'):
                    assert first[key]==second[key]
                assert (first['error'] or {}).get('error_type')==(second['error'] or {}).get('error_type')
                np.testing.assert_allclose(first['evaluation']['position'],second['evaluation']['position'],atol=1e-8,rtol=0)
        checked.append(dict(arm=arm,modes=3,physical_outcomes_equal=True))
    return checked


def totals(rows):
    keys = sorted({(r['item']['study'],r['item'].get('mode','all'),r['item']['arm']) for r in rows})
    values = []
    for study,mode,arm in keys:
        group = [r for r in rows if (r['item']['study'],r['item'].get('mode','all'),r['item']['arm'])==(study,mode,arm)]
        values.append(dict(study=study,mode=mode,arm=arm,runs=len(group),successes=sum(r['success'] for r in group),
                           physical_attempts=sum(r['attempts'] for r in group),
                           **{k:sum(r['audit'][k] for r in group) for k in ('calls','invalid','service_errors','model_latency_s')}))
    return values


def compare_methods(rows):
    comparisons = []
    for model in rows:
        item = model['item']
        if item['arm'] not in ('guided','hybrid'):
            continue
        baseline_arm = 'priority' if item['study']=='feedback' else 'rule_stage'
        same_group = lambda r: r['item']['study']==item['study'] and (
            r['item'].get('mode')==item.get('mode') and r['item'].get('scene_id')==item.get('scene_id'))
        baseline = next((r for r in rows if same_group(r) and r['item']['arm']==baseline_arm),None)
        if baseline is None:
            continue
        actions = lambda r:[v['changes'] for v in r['trajectory']]
        comparisons.append(dict(model_id=item['id'],baseline_id=baseline['item']['id'],
                                same_actions=actions(model)==actions(baseline),
                                model_success=model['success'],baseline_success=baseline['success']))
    return comparisons


def main():
    protocol = verify()
    rows = [row(r) for r in protocol['items'] if (ROOT/'tasks'/r['id']/'summary.json').exists()]
    pending = [r['id'] for r in protocol['items'] if r['id'] not in {v['item']['id'] for v in rows}]
    result = dict(expected=35,completed=len(rows),pending=pending,rows=rows,metrics=totals(rows),
                  negative_controls=negative_controls(protocol['items'],rows),
                  comparisons=compare_methods(rows),
                  training_approved=0,test_used=False,training_started=False,expansion_started=False)
    atomic(ROOT/'verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pending')},ensure_ascii=False))


if __name__=='__main__':
    main()
