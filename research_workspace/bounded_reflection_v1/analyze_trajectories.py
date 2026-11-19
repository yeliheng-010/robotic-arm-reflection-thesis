"""派生动作轨迹摘要；只读冻结结果，不执行仿真或模型请求。"""
import json
from bounded.protocol import ROOT,verify
from controlled.worker import jsonlines
from stability.collection_status import atomic


def describe(item):
    directory = ROOT/'physical/tasks'/item['id']
    result = json.loads((directory/'result.json').read_text())
    feedback = {e['attempt']:e for e in jsonlines(directory/'feedback.jsonl')}
    records = []
    for record in result['records']:
        report = feedback.get(record['attempt'],{}).get('projected',{})
        evidence = report.get('evidence',{})
        error = record.get('error') or {}
        records.append(dict(attempt=record['attempt'],accepted=record['accepted'],
                            error=error.get('error_type'),
                            segment=record.get('diagnostics',{}).get('motion_segment'),
                            changes=record.get('reflection',{}).get('changes'),
                            projected_grasp_residual=evidence.get('grasp_residual_xy'),
                            projected_place_residual=evidence.get('placement_residual_xy')))
    return dict(id=item['id'],case=item['case'],arm=item['arm'],repeat=item['repeat'],
                success=result['success'],records=records)


def main():
    rows = [describe(item) for item in verify()['closed_loop']]
    priorities = {r['case']:r for r in rows if r['arm']=='priority'}
    comparisons = []
    for row in rows:
        if row['arm']!='hybrid':
            continue
        baseline = priorities[row['case']]
        same = [r['changes'] for r in row['records']]==[r['changes'] for r in baseline['records']]
        comparisons.append(dict(id=row['id'],same_actions_as_priority=same,
                                same_outcome=row['success']==baseline['success']))
    result = dict(rows=rows,hybrid_vs_priority=comparisons,
                  training_approved=0,test_used=False)
    atomic(ROOT/'trajectories.json',result)
    print(json.dumps(comparisons))


if __name__=='__main__':
    main()
