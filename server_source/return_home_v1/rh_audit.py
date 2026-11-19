"""独立复算选路与实际命令，再执行原完整物理审计。"""
import sys
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import rb_audit
import geometry_v3
import sv_strategy_audit
from audit_v5 import audit_attempt
from iv3_geometry import strict_compare, ReconstructionMismatch
from audit_motion_live import rebuild, UR5e, set_robot_config, guard_context
from self_geometry import context as self_context
from bounded_ik_v2 import context as joint_context
from ta_audit import observations
from live_motion import plan_values
from sr_audit import measured
from cc_common import read, save, sha, verify
from rh_planner import select, planners
from rh_prepare import REPAIR, SOURCE


def return_audit(case, folder):
    recorded = read(folder/'return_plan.json')
    with patch.object(UR5e, 'set_robot_config', set_robot_config), \
         guard_context(case['item'], {}), self_context(), joint_context(case['config']):
        robot, env = rebuild(case, recorded['context'])
        actual = select(robot, env, recorded['goal'],
            duration=recorded['original_duration'], item=case['item'])
    assert actual == recorded['result']
    option = actual['selected']
    if option is None:
        return dict(selected=None, independently_reproduced=True)
    segments = [('back_to_zero_'+str(i), p, t)
                for i, (p, t) in enumerate(zip(planners(option), option['durations']))]
    executed = read(folder/'bridge.json')['planners'][-1]
    assert executed['executed'] and executed['action'] == 'back_to_zero'
    assert plan_values(segments) == executed['legs']
    assert executed['durations'] == [0., *option['durations']]
    np.testing.assert_array_equal(executed['context']['robot_q'], option['waypoints'][0])
    return dict(selected=option['id'], independently_reproduced=True,
                duration=sum(option['durations']), command_samples_identical=True)


def inspect(case, *, base):
    folder = base/'cases'/str(case['item']['seed'])/'first'
    step = read(folder/'step.json')
    result = read(folder.parent/'result.json')
    assert step['index'] == result['physical_attempts'] == 1
    assert step['state'] == case['state'] and step['strategy'] == case['strategy']
    seen = observations(case, folder)
    assert result['public_input_allowed'] == seen['final']['accepted']
    route = return_audit(case, folder) if (folder/'return_plan.json').exists() else None
    contact = measured(folder)
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
    return dict(passed=True, success=step['success'], observations=seen, return_route=route,
                geometry=evidence['geometry'], contact=evidence['contact'])


if __name__ == '__main__':
    seed = int(sys.argv[1])
    manifest = verify(REPAIR/'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['seed'] == seed)
    source = read(SOURCE/'manifest.json')
    assert case == next(c for c in source['cases'] if c['item']['seed'] == seed)
    value = inspect(case, base=REPAIR)
    paths = [p for p in (REPAIR/'cases'/str(seed)).rglob('*') if p.is_file()]
    value.update(identities={str(p): sha(p) for p in paths}, manifest_sha256=sha(REPAIR/'manifest.json'))
    save(REPAIR/'audits'/(str(seed)+'.json'), value)
    print(dict(seed=seed, passed=value['passed'], success=value.get('success')), flush=True)
