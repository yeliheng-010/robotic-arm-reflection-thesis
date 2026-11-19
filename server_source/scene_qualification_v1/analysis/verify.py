"""独立读取资格筛选的全部条件，复核跳过原因与有效配对。"""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path('/home/yeliheng/grasp_server/scene_qualification_v1')
sys.path.insert(0,str(ROOT))
from protocol import verify
from design import build,qualify
from stability.collection_status import atomic


def audit_arm(item,enabled):
    directory = ROOT/'runs'/item['id']/str(int(enabled))
    result = json.loads((directory/'result.json').read_text())
    row = json.loads((directory/'summary.json').read_text())
    assert result['scenario']==build(item['seed'],item['factor'])
    assert result['attempts']==1 and not result['llm_stats']
    record = result['records'][0]
    assert row['success']==result['success']==record['accepted']
    error = record.get('error') or {}
    contacts = error.get('evidence',{}).get('contacts',[])
    assert row['enabled']==enabled and row['contacts']==contacts
    assert row['error']==error.get('error_type')
    assert row['segment']==record.get('diagnostics',{}).get('motion_segment')
    collision = error.get('error_type')=='collision' and any('SafetyDivider' in p for p in contacts)
    assert collision==row['intended_collision']
    row['result_sha256'] = hashlib.sha256((directory/'result.json').read_bytes()).hexdigest()
    return row


def audit_pair(item):
    directory = ROOT/'runs'/item['id']
    pair = json.loads((directory/'pair.json').read_text())
    assert pair['item']==item
    row = dict(id=item['id'],source=item['source'],seed=item['seed'],factor=item['factor'],
               status=pair['status'],executed=pair['executed'],qualified=False)
    if not pair['geometry']['passed']:
        assert pair['status']=='geometry_ineligible' and pair['executed']==0
        return row
    control = audit_arm(item,False)
    row.update(control_success=control['success'],control_error=control['error'])
    if not control['success']:
        assert pair['status']=='not_run_control_failed' and not (directory/'1').exists()
        assert pair['executed']==1
        return row
    treatment = audit_arm(item,True)
    for field in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_allclose(control['trace'][field],treatment['trace'][field],atol=1e-8,rtol=0)
    qualified = qualify(True,treatment['intended_collision'],treatment['segment'],paired=True)
    assert pair['qualified']==qualified and pair['executed']==2
    row.update(treatment_error=treatment['error'],segment=treatment['segment'],qualified=qualified,
               intended_contact=treatment['intended_collision'],paired_initial_state=True,
               control_sha256=control['result_sha256'],treatment_sha256=treatment['result_sha256'])
    return row


def main():
    protocol = verify()
    rows = [audit_pair(item) for item in protocol['items'] if (ROOT/'runs'/item['id']/'pair.json').exists()]
    result = dict(expected_conditions=12,completed_conditions=len(rows),planned_runs=24,
                  actual_runs=sum(r['executed'] for r in rows),
                  control_successes=sum(r.get('control_success',False) for r in rows),
                  qualified=sum(r['qualified'] for r in rows),rows=rows,test_used=False,
                  model_calls=0,training_approved=0)
    atomic(ROOT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
