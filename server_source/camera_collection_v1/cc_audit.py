"""独立进程审计一次物理执行及初态/暂停态可见性。"""
import sys
from pathlib import Path
from unittest.mock import patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import rb_audit
import geometry_v3
import sv_strategy_audit
from audit_v5 import audit_attempt
from iv3_geometry import strict_compare, ReconstructionMismatch
from nc_audit_frames import frame
from sr_audit import measured
from cv_select import scene, evaluate
from cv_policy import REQUIRED, frame_gate
from sd_inventory import root_boxes
from cc_common import PILOT, current, read, save, sha


def visibility(path, config):
    recorded = read(path)
    assert sha(recorded['state_path']) == recorded['state_sha256']
    with scene(config) as (env, renderer):
        with np.load(recorded['state_path']) as snapshot:
            mujoco.mj_setState(env.mj_model, env.mj_data, snapshot['state'], mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model, env.mj_data)
        boxes = root_boxes(env.mj_model, env.mj_data)
        actual = evaluate(env, renderer, config['camera'], boxes={n: boxes[n] for n in REQUIRED})
    assert actual['measurements'] == recorded['measurements']
    assert actual['accepted'] == recorded['accepted']
    assert frame_gate(recorded['measurements']) == recorded['gate']
    return dict(accepted=actual['accepted'], identical_measurements=True)


def inspect(case):
    folder = PILOT/'cases'/str(case['item']['seed'])
    result, step = read(folder/'result.json'), read(folder/'first/step.json')
    assert result['physical_attempts'] == step['index'] == 1
    assert result['manifest_sha256'] == sha(PILOT/'manifest.json')
    initial = visibility(folder/'first/initial_visibility.json', case['config'])
    assert initial['accepted']
    final = visibility(folder/'first/observations/visibility_0.json', case['config'])
    assert final['accepted'] == result['public_input_allowed']
    summary = read(folder/'first/observation_summary.json')
    source = Path(summary['paths'][0])
    expected = folder/'first'/('observations' if final['accepted'] else 'private_audit')/'observation_0'
    assert source == expected
    public, private = frame(source, case['config'], attempt=1, index=0)
    assert summary['public'] == [public] and summary['private'] == [private]
    contact = measured(folder/'first')
    if contact['self_contact_samples']:
        return dict(passed=False, reason='measured_robot_self_contact')
    with patch.object(geometry_v3, 'compare', strict_compare), \
         patch.object(rb_audit, 'geometry', geometry_v3.audit), \
         patch.object(sv_strategy_audit, 'audit_attempt', audit_attempt):
        try:
            evidence = sv_strategy_audit.inspect(case, step)
        except ReconstructionMismatch as error:
            return dict(passed=False, reason='dynamic_geometry_reconstruction_mismatch', evidence=error.evidence)
    assert step['success'] == result['new_success']
    old = read(case['camera_collection']['old_step'])
    assert old['state'] == step['state'] and old['strategy'] == step['strategy']
    return dict(passed=True, old_success=old['success'], new_success=result['new_success'],
        initial=initial, final=final, geometry=evidence['geometry'], contact=evidence['contact'])


if __name__ == '__main__':
    case = current(int(sys.argv[1]))
    result = inspect(case)
    paths = [p for p in (PILOT/'cases'/str(case['item']['seed'])).rglob('*') if p.is_file()]
    result.update(identities={str(p): sha(p) for p in paths}, manifest_sha256=sha(PILOT/'manifest.json'))
    save(PILOT/'audits'/(str(case['item']['seed'])+'.json'), result)
    print(dict(seed=case['item']['seed'], passed=result['passed']), flush=True)
