"""原物理审计加实际目标姿态、输入不变及完整分母检查。"""
import numpy as np
import spatialmath as sm
from semanticfix2.audit import audit as previous_audit
from posecheck2.adapter import YAW_DEGREES


def audit(result,item):
    checked = previous_audit(result,item)
    trace = result['records'][0]['execution_adapter']
    assert trace['yaw_deg']==item['yaw_deg']
    assert trace['source']=='fixed_executor_pose_diagnostic'
    assert trace['execution_entered'] and trace['observation_state_unchanged']
    assert trace['keep_orientation']==(item['yaw_deg']==0)
    target = np.array(trace['planned_poses'][-1])
    np.testing.assert_allclose(trace['target_xyz'],target[:3,3],atol=1e-12,rtol=0)
    expected = sm.SO3.Rz(item['yaw_deg'],unit='deg').R@np.array(trace['start'])[:3,:3]
    np.testing.assert_allclose(expected,target[:3,:3],atol=1e-12,rtol=0)
    assert trace['lift_height']==item['parameters']['lift_height']==.45
    if item['yaw_deg']==0:
        assert [r['yaw_deg'] for r in trace['static']]==list(YAW_DEGREES)
        assert all(len(r['rows'])==153 for r in trace['static'])
    checked['adapter_verified'] = True
    return checked
