"""基于可观测测量构造候选；不接收故障标签或预设正确动作。"""
import math

CLEARANCE_MARGIN_M = .05
TIME_MULTIPLIER = 1.5
DECIMALS = 10
EFFECTS = {
    'align_grasp': '平移抓取指令以减小抓取XY残差；不直接改变释放点或越障高度。',
    'align_release': '平移释放指令以减小最终位置XY残差；不直接保证姿态或抓取稳定。',
    'clear_contact': '增加横向搬运前抬升距离，令被搬物底部高于接触障碍顶面；可能遇到IK或其他障碍。',
    'slow_motion': '延长原轨迹的执行时间；空间路径不变，不能绕过固定障碍。',
    'replan': '请求重新规划；当前仿真路径仍使用标准动作序列，不自动创建新的空间避障路线。',
    'reground': '请求重新定位；当前仿真定位仍由同一场景观测产生，不自动创建新抓取候选。',
}


def finite_vector(value, length):
    return isinstance(value, (tuple, list)) and len(value) == length and all(
        type(v) in (int, float) and math.isfinite(v) for v in value)


def alignment(evidence, parameters, *, field, measurement):
    residual = evidence.get(measurement)
    if not finite_vector(residual, 2):
        return None
    current = getattr(parameters, field)
    vector = [round(current[i] - residual[i], DECIMALS) for i in range(2)] + [current[2]]
    return {field: vector}


def clearance(evidence, parameters, *, source):
    bounds = evidence.get('diagnostics', {}).get('contact_bounds_world', [])
    valid = [b for b in bounds if isinstance(b, dict)
             and finite_vector(b.get('lower_xyz'), 3) and finite_vector(b.get('upper_xyz'), 3)]
    payload = next((b for b in valid if b.get('body') == source), None)
    obstacles = [b for b in valid if b.get('body') != source]
    if payload is None or not obstacles:
        return None
    gap = max(b['upper_xyz'][2] for b in obstacles) - payload['lower_xyz'][2]
    increase = max(0., gap) + CLEARANCE_MARGIN_M
    return {'lift_height': round(parameters.lift_height + increase, DECIMALS)}


def append_valid(rows, parameters, *, identity, changes):
    if changes is None:
        return
    try:
        updated = parameters.updated(changes)
    except (ValueError, TypeError):
        return
    if updated != parameters:
        rows.append({'id': identity, 'changes': changes, 'effect': EFFECTS[identity]})


def build_candidates(report, parameters, *, source):
    evidence, rows = report.get('evidence', {}), []
    options = {
        'align_grasp': alignment(evidence, parameters, field='grasp_offset', measurement='grasp_residual_xy'),
        'align_release': alignment(evidence, parameters, field='place_offset', measurement='placement_residual_xy'),
        'clear_contact': clearance(evidence, parameters, source=source),
        'slow_motion': {'time_scale': round(parameters.time_scale * TIME_MULTIPLIER, DECIMALS)},
        'replan': {'replan': True}, 'reground': {'reground': True},
    }
    for identity, changes in options.items():
        append_valid(rows, parameters, identity=identity, changes=changes)
    return rows
