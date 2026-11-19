"""从原始记录重新计算碰撞校准资格，保留无效条件分母。"""
import hashlib
import json
import numpy as np
from stability.collection_status import atomic
from calibrate import ROOT, items, verify


def inspect_row(item):
    directory = ROOT/'runs'/item['id']
    row = json.loads((directory/'summary.json').read_text())
    geometry = json.loads((directory/'geometry.json').read_text())
    assert row['item']==item and geometry['passed']
    result = json.loads((directory/'result.json').read_text())
    record = result['records'][0]
    assert result['attempts']==1 and not result['llm_stats']
    assert result['success']==row['success']==record['accepted']
    error = record.get('error') or {}
    contacts = error.get('evidence',{}).get('contacts',[])
    actual = error.get('error_type')=='collision' and any('SafetyDivider' in p for p in contacts)
    assert actual == row['intended_collision']
    return dict(id=item['id'],source=item['source'],seed=item['seed'],enabled=item['enabled'],
                success=row['success'],error=error.get('error_type'),
                segment=(record.get('diagnostics') or {}).get('motion_segment'),
                intended_collision=actual,contacts=contacts,initial=row['trace'],
                source_hashes={name:hashlib.sha256((directory/name).read_bytes()).hexdigest()
                               for name in ('result.json','summary.json','geometry.json')})


def main():
    verify()
    final = json.loads((ROOT/'result.json').read_text())
    assert final['status']=='completed' and final['completed']==final['expected']==12
    rows = [inspect_row(item) for item in items()]
    pairs = []
    for control,treatment in zip(rows[::2],rows[1::2]):
        for field in ('initial_qpos','initial_body_xyz'):
            np.testing.assert_allclose(control['initial'][field],treatment['initial'][field],atol=1e-8,rtol=0)
        qualified = control['success'] and treatment['intended_collision'] and treatment['segment'] in ('lift','transport')
        pairs.append(dict(source=control['source'],seed=control['seed'],control_success=control['success'],
                          control_error=control['error'],treatment_error=treatment['error'],
                          treatment_segment=treatment['segment'],qualified=qualified,
                          intended_contact=treatment['intended_collision']))
    for row in rows:
        row.pop('initial')
    output = dict(passed=True,runs=12,paired_initial_states=6,qualified_pairs=sum(p['qualified'] for p in pairs),
                  all_controls_successful=all(p['control_success'] for p in pairs),pairs=pairs,rows=rows,
                  test_used=False,model_calls=0,training_approved=0)
    atomic(ROOT/'verification.json',output)
    print(json.dumps({k:v for k,v in output.items() if k!='rows'},ensure_ascii=False))


if __name__ == '__main__':
    main()
