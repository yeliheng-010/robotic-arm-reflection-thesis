"""只读检查缓存与 qpos 重建差异，保留全部已消费轨迹。"""
import os
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
import mujoco
from reflection.__main__ import bootstrap
bootstrap()
from collection_common import PHYSICS, read, save, sha, verify

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'recovery_integrity_v2'))
from ig_audit import case_steps, contact_evidence
from route_audit_v3 import rebuild
from goal_geometry import geometry
from geometry_consistency import compare
from manipulator_grasp.arm.robot import UR5e
from stability.kinematics import set_robot_config

NAME = 'R1_964194_varied_noisy'


def inspect_step(case, step):
    trace = read(Path(step['session_path']) / 'route.json')
    if 'endpoints' not in trace:
        return dict(path=step['session_path'], no_endpoint=True)
    with patch.object(UR5e, 'set_robot_config', set_robot_config):
        flow = rebuild(case, trace)
    current = geometry(flow, case['item'])
    cached = trace['endpoints']['geometry']
    deltas = {k: (np.asarray(current[k])-np.asarray(cached[k])).tolist() for k in cached}
    try:
        checked = compare(cached, current)
    except AssertionError as error:
        checked = dict(passed=False, error=repr(error))
    data, model = flow.env.mj_data, flow.env.mj_model
    before = data.qpos.copy()
    mujoco.mj_forward(model, data)
    repeated = geometry(flow, case['item'])
    assert np.array_equal(before, data.qpos) and repeated == current
    body = model.body(case['item']['source']).id
    joint = int(model.body_jntadr[body])
    address = int(model.jnt_qposadr[joint])
    return dict(path=step['session_path'], cached=cached, reconstructed=current,
        deltas=deltas, comparison=checked, qpos_unchanged=True, forward_repeat_exact=True,
        object_qpos=data.qpos[address:address+7].tolist(), timestep=float(model.opt.timestep),
        selected=trace['selected'] is not None)


def inventory(manifest):
    rows = []
    for case in manifest['cases']:
        name = case['item']['id']
        folder = PHYSICS / 'cases' / name
        result = read(folder / 'result.json') if (folder / 'result.json').exists() else None
        rows.append(dict(id=name, exists=folder.exists(), result=result,
            accepted=(PHYSICS / 'audits' / (name+'.json')).exists(),
            rejected=(PHYSICS / 'audit_rejections' / (name+'.json')).exists()))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID') and PHYSICS.parent.name == '006'
    manifest = verify(PHYSICS / 'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['id'] == NAME)
    folder, result, steps = case_steps(case)
    _, contacts = contact_evidence(case)
    files = [p for p in folder.rglob('*') if p.is_file()]
    identities = {str(p): sha(p) for p in files}
    rows = [inspect_step(case, step) for step in steps.values()]
    assert all(sha(p) == h for p, h in identities.items())
    output = dict(case=NAME, attempts=result['attempts'], rows=rows, contacts=contacts,
        inventory=inventory(manifest), identities=identities,
        manifest_sha256=sha(PHYSICS / 'manifest.json'), physical_attempts=0, model_calls=0)
    save(ROOT / 'results' / ('job_'+os.environ['SLURM_JOB_ID']+'.json'), output)
    print(dict(rows=rows, contacts=contacts, inventory=output['inventory']), flush=True)


if __name__ == '__main__':
    main()
