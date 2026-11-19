"""从冻结协议及原始结果复核物理结果和静态诊断。"""
import json
import sys
from pathlib import Path
import numpy as np
from collections import Counter

ROOT = Path('/home/yeliheng/grasp_server/descent_pose_v2')
sys.path.insert(0,str(ROOT))
from posecheck2.protocol import verify
from posecheck2.audit import audit
from semanticfix2.protocol import sha
from stability.collection_status import atomic


def static_summary(trace):
    rows = []
    for value in trace.get('static',[]):
        points = value['rows']
        assert value['collision_samples']==sum(bool(r.get('arm_contacts')) for r in points)
        assert value['ik_failures']==sum(not r['ik'] for r in points)
        assert value['endpoint']==points[-1]
        rows.append(dict(yaw_deg=value['yaw_deg'],ik_failures=value['ik_failures'],
            collision_samples=value['collision_samples'],endpoint_ik=value['endpoint']['ik'],
            endpoint_contacts=value['endpoint'].get('arm_contacts'),
            endpoint_clearance_m=value['endpoint'].get('wrist_divider_distance'),
            collision_phases=dict(Counter(r['phase'] for r in points if r.get('arm_contacts')))))
    return rows


def read_row(item):
    directory = ROOT/'physical/tasks'/item['id']
    result = json.loads((directory/'result.json').read_text())
    saved = json.loads((directory/'summary.json').read_text())
    record = result['records'][0]
    assert saved['audit']==audit(result,item)
    assert saved['success']==result['success'] and saved['evaluation']==record['evaluation']
    assert saved['id']==item['id'] and saved['yaw_deg']==item['yaw_deg']
    baseline = ROOT.parent/'feedback_semantics_v2/physical/tasks'/f"{item['scene_id']}_lift45/result.json"
    old = json.loads(baseline.read_text())['records'][0]
    assert old['parameters']==record['parameters']
    for field in ('initial_qpos','initial_body_xyz'):
        np.testing.assert_allclose(old['candidate_trace'][field],record['candidate_trace'][field],atol=1e-8,rtol=0)
    trace = record['execution_adapter']
    details = (record.get('error') or {}).get('evidence',{}).get('contact_details',{})
    bodies = sorted({g['body'] for c in details.get('contacts',[]) for g in c['geometries'] if g['body']!='SafetyDivider'})
    return dict(**saved,actual_bodies=bodies,static=static_summary(trace),
        result_sha256=sha(directory/'result.json'),baseline_sha256=sha(baseline))


def main():
    protocol = verify()
    rows = [read_row(i) for i in protocol['items'] if (ROOT/'physical/tasks'/i['id']/'summary.json').exists()]
    assert len(rows)==len({r['id'] for r in rows})
    metrics = [dict(yaw_deg=y,n=sum(r['yaw_deg']==y for r in rows),
        successes=sum(r['success'] for r in rows if r['yaw_deg']==y)) for y in (0,-45,45,-90,90)]
    output = dict(expected=10,completed=len(rows),rows=rows,metrics=metrics,
        unchanged_baselines=sum(r['audit']['unchanged_physics_at_same_parameters'] for r in rows),
        source='fixed_executor_pose_diagnostic',model_calls=0,training_approved=0,test_used=False,
        protocol_sha256=sha(ROOT/'protocol.json'))
    atomic(ROOT/'verification.json',output)
    print(json.dumps({k:v for k,v in output.items() if k!='rows'}))


if __name__=='__main__':
    main()
