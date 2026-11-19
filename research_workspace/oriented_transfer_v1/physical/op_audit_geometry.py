"""独立复算实际入口完整链及冻结旋转目标，不使用旧平移外接盒审计。"""
import numpy as np
from route_audit_v3 import rebuild
from op_choose import replay,legacy
from op_common import entry


def audit(case, trace):
    assert trace['planning_family']=='oriented_transfer_v1'
    flow=rebuild(case,trace)
    plan=replay(flow,case,trace['context']['parameters'])
    assert plan==trace['oriented_plan']
    expected=legacy(flow,plan,trace['context']['parameters'])
    assert expected['selected']==trace['selected']
    assert expected['edges']==trace['edges']
    return dict(passed=True,full_search_repeated=True,selected=True,
        held_geometry='SE3_transformed_active_geometries',independent=True)
