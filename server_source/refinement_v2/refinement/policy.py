"""仅使用展示反馈的有界专家策略；不为模型修补回答。"""
from reflection.reflector import Reflection
from controlled.feedback import check_action

OFFSET_LIMIT = .25
RESIDUAL_THRESHOLD = .015
SLOW_FACTOR = 1.5
MAX_DURATION = 3.
MIN_CLEARANCE = .45
MAX_LIFT = .48
LIFT_STEP = .10
PROBES = ((.02, 0.), (-.02, 0.), (0., .02), (0., -.02))
PREGRASP = ('pregrasp', 'approach', 'grasp')


class PolicyExhausted(RuntimeError):
    """预先定义的合法策略已经用尽；仍计为任务失败。"""


def compensation(parameters, evidence, *, field, measurement):
    residual = evidence.get(measurement)
    if residual is None:
        return None
    old = getattr(parameters, field)
    corrected = [max(-OFFSET_LIMIT, min(OFFSET_LIMIT, old[i]-residual[i])) for i in range(2)]
    corrected.append(old[2])
    return {field: corrected}


def grasp_options(parameters, evidence):
    residual = evidence.get('grasp_residual_xy')
    if residual is not None and max(abs(v) for v in residual) > RESIDUAL_THRESHOLD:
        yield 'measured_grasp_compensation', compensation(
            parameters, evidence, field='grasp_offset', measurement='grasp_residual_xy')
    count = evidence.get('diagnostics', {}).get('available_candidate_count')
    if count is not None and parameters.candidate_index+1 < min(count, 5):
        yield 'next_available_grasp', {'candidate_index': parameters.candidate_index+1}


def placement_options(parameters, evidence, history):
    if evidence.get('placement_residual_xy') is not None:
        yield 'measured_placement_compensation', compensation(
            parameters, evidence, field='place_offset', measurement='placement_residual_xy')
        return
    tried = sum('missing_measurement_probe' in h['reflection']['cause'] for h in history)
    for xy in PROBES[tried:]:
        offset = [max(-OFFSET_LIMIT, min(OFFSET_LIMIT, parameters.place_offset[i]+xy[i])) for i in range(2)]
        yield 'missing_measurement_probe', {'place_offset': [*offset, parameters.place_offset[2]]}


def options(report, parameters, history):
    kind, evidence = report.error_type.value, report.evidence
    phase = evidence.get('diagnostics', {}).get('motion_segment')
    if kind in ('placement_offset', 'object_outside_container'):
        yield from placement_options(parameters, evidence, history)
    elif kind in ('empty_grasp', 'ik_failure', 'object_dropped'):
        yield from grasp_options(parameters, evidence)
    elif kind == 'collision':
        if phase in PREGRASP:
            yield from grasp_options(parameters, evidence)
        elif phase == 'transport':
            height = min(MAX_LIFT, max(MIN_CLEARANCE, parameters.lift_height+LIFT_STEP))
            yield 'transport_clearance', {'lift_height': height}
    else:
        if kind != 'object_toppled':
            return
    yield 'bounded_duration_increase', {'time_scale': min(MAX_DURATION, parameters.time_scale*SLOW_FACTOR)}


class BoundedRule:
    def reflect(self, report, parameters, history=()):
        count = report.evidence.get('diagnostics', {}).get('available_candidate_count')
        for cause, changes in options(report, parameters, history):
            answer = Reflection(cause, changes, 'rule_v2')
            try:
                check_action(answer, parameters, candidate_count=count)
            except ValueError:
                continue
            return answer
        raise PolicyExhausted('No remaining legal action in the declared expert policy')
