"""逐采样对比两种旋转时机；不把静态判据当作物理成功。"""
import json
from pathlib import Path
import numpy as np

BASE = Path('/home/yeliheng/grasp_server')


def read(root,factor):
    path = BASE/root/'physical/tasks'/f'Q1_905001_{factor}_lift45/result.json'
    return json.loads(path.read_text())['records'][0]['execution_adapter']


def compare(factor):
    old,new = read('descent_pose_v2',factor),read('descent_route_v1',factor)
    assert old['durations']==new['durations'] and old['dt']==new['dt']
    assert old['target_xyz']==new['target_xyz'] and old['joint_config']==new['joint_config']
    np.testing.assert_allclose(old['start'],new['start'],atol=1e-12,rtol=0)
    rows = []
    for before,after in zip(old['static'],new['static']):
        assert before['yaw_deg']==after['yaw_deg']
        assert len(before['rows'])==len(after['rows'])==153
        for a,b in zip(before['rows'],after['rows']):
            assert (a['phase'],a['time'])==(b['phase'],b['time'])
            np.testing.assert_allclose(a['xyz'],b['xyz'],atol=1e-12,rtol=0)
        rows.append(dict(factor=factor,yaw_deg=before['yaw_deg'],positions_equal=153,
            old_ik_failures=before['ik_failures'],new_ik_failures=after['ik_failures'],
            old_collision_samples=before['collision_samples'],new_collision_samples=after['collision_samples']))
    return rows


if __name__=='__main__':
    rows = compare('position_only')+compare('yaw_only')
    result = dict(passed=True,paired_samples=sum(r['positions_equal'] for r in rows),rows=rows,
                  scope='same_position_and_timing_static_comparison_not_closed_loop')
    (BASE/'descent_route_v1/path_comparison.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result))
