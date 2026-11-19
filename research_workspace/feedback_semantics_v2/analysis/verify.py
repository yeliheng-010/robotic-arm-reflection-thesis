"""复算全部固定诊断，不筛掉失败条件。"""
import json
from collections import Counter
from pathlib import Path
import sys

ROOT = Path('/home/yeliheng/grasp_server/feedback_semantics_v2')
sys.path.insert(0,str(ROOT))
from semanticfix2.protocol import verify,sha
from semanticfix2.audit import audit
from stability.collection_status import atomic


def read_row(item):
    directory = ROOT/'physical/tasks'/item['id']
    result = json.loads((directory/'result.json').read_text())
    verified = audit(result,item)
    saved = json.loads((directory/'summary.json').read_text())
    assert verified==saved['audit'] and saved['success']==result['success']
    record = result['records'][0]
    evidence = (record.get('error') or {}).get('evidence',{})
    contacts = evidence.get('contact_details',{}).get('contacts',[])
    return dict(**saved,parameters=record['parameters'],result_sha256=sha(directory/'result.json'),
                actual_bodies=sorted({g['body'] for c in contacts for g in c['geometries'] if g['body']!='SafetyDivider'}))


def main():
    protocol = verify()
    rows = [read_row(i) for i in protocol['items'] if (ROOT/'physical/tasks'/i['id']/'summary.json').exists()]
    totals = [dict(variant=v,runs=sum(r['variant']==v for r in rows),
                   successes=sum(r['success'] for r in rows if r['variant']==v))
              for v in dict.fromkeys(i['variant'] for i in protocol['items'])]
    result = dict(expected=22,completed=len(rows),rows=rows,metrics=totals,
                  same_parameter_physics_checks=sum(r['audit']['unchanged_physics_at_same_parameters'] for r in rows),
                  phases=dict(Counter(r['phase'] for r in rows if not r['success'])),
                  source='fixed_diagnostic_intervention',model_calls=0,training_approved=0,test_used=False)
    atomic(ROOT/'verification.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))


if __name__=='__main__':
    main()
