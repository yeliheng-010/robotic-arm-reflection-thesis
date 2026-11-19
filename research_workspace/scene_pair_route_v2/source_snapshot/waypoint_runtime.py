"""仅规划拒绝后的一次继续机会；规划与执行共用路点构造。"""
from contextlib import contextmanager
from unittest.mock import patch
import numpy as np
import spatialmath as sm
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import stability.prepose as prepose
from reflection.monitors import abort, ErrorType
from waypoint_policy import allowed
from waypoint_paths import detour, inject
from waypoint_search import choose


def selector(item, parameters, trace, *, hooks):
    def run(flow, *, ignore):
        plan = choose(flow, item=item, parameters=parameters, hooks=hooks)
        trace.update(plan)
        selected = plan['selected']
        if selected is None:
            abort(ErrorType.COLLISION, 'No certified waypoint route', route_planning_rejected=True,
                  evaluated_prefixes=len(plan['prefixes']), evaluated_carry=len(plan['candidates']))
        flow.T_wo, flow.q1 = sm.SE3(np.array(selected['pose'])), np.array(selected['q1'])
        return dict(changed=True, q1=selected['q1'], config=selected['config'], route_id=selected['id'])
    return run


def prefix_wrapper(original, trace):
    def move(*args, **kwargs):
        selected, counter = trace['selected'], [0]
        backend = grasp._run_planners
        def run(*values, **named):
            assert not named and len(values[2]) == 1
            changed = list(values)
            if counter[0] == 1:
                planner, seconds = detour(values[2][0], values[3][1],
                    route=selected['approach_route'], edges=np.array(trace['edges']))
                changed[2], changed[3] = [planner], [0., seconds]
            counter[0] += 1
            return backend(*changed)
        with patch.object(grasp, '_run_planners', run):
            result = original(*args, **kwargs)
        assert counter[0] == 3
        return result
    return move


def carry_wrapper(original, trace):
    def move(*args, **kwargs):
        selected = trace['selected']
        assert kwargs.get('keep_orientation', True)
        kwargs['lift_height'] = selected['lift']
        backend = inject(grasp._run_planners, selected['transport_route'], edges=np.array(trace['edges']))
        with patch.object(grasp, '_run_planners', backend):
            return original(*args, **kwargs)
    return move


@contextmanager
def context(item, state, trace, *, previous_record, previous_trace):
    active = allowed(previous_record, previous_trace, item['destination'])
    trace.update(active=active, prior_rejection=active, collision_feedback=previous_trace.get('feedback'))
    if not active:
        yield
        return
    assert state['profile'] == 'original'
    hooks = grasp.move_to_grasp_pose, grasp.move_to_point
    with patch.object(prepose, 'select_prepose', selector(item, state['parameters'], trace, hooks=hooks)), \
         patch.object(grasp, 'move_to_grasp_pose', prefix_wrapper(hooks[0], trace)), \
         patch.object(grasp, 'move_to_point', carry_wrapper(hooks[1], trace)):
        yield
