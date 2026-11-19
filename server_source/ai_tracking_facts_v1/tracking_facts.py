"""由同一时刻命令和编码器派生误差，不读取原因标签、接触真值或未来结果。"""
import math

ACTIONS = ('move_to_grasp_pose', 'close_gripper', 'move_to_point', 'open_gripper', 'back_to_zero')


def vector(value):
    if len(value) != 3 or not all(math.isfinite(float(x)) for x in value):
        raise ValueError('Expected a finite 3D position')
    return [float(x) for x in value]


def sample(row):
    command, actual = vector(row['command_tcp_xyz_m']), vector(row['tcp_fk_xyz_m'])
    time, gripper = float(row['time_s']), float(row['gripper_joint_rad'])
    if not math.isfinite(time) or not math.isfinite(gripper):
        raise ValueError('Nonfinite encoder sample')
    delta = [a-c for a,c in zip(actual, command)]
    return dict(time_s=time, commanded_tcp_xyz_m=command, encoder_fk_tcp_xyz_m=actual,
                actual_minus_command_m=delta, position_error_m=math.sqrt(sum(x*x for x in delta)),
                gripper_joint_rad=gripper)


def summarize(rows):
    grouped = {name:[] for name in ACTIONS}
    previous = -math.inf
    for row in rows:
        current = sample(row)
        if current['time_s'] < previous:
            raise ValueError('Telemetry must be chronological')
        previous = current['time_s']
        if row['action'] in grouped:
            grouped[row['action']].append(current)
    facts = []
    for action, values in grouped.items():
        if values:
            facts.append(dict(action=action, sampled_count=len(values), first=values[0], last=values[-1],
                max_sampled_position_error_m=max(v['position_error_m'] for v in values),
                gripper_joint_change_rad=values[-1]['gripper_joint_rad']-values[0]['gripper_joint_rad']))
    return dict(source='simulated_joint_encoders_forward_kinematics_and_commanded_tcp', actions=facts,
        interpretation='Samples show commanded versus measured position; gripper angle is not proof of holding an object.',
        limitation='End means last recorded sample in an action, including an aborted action; no cause label is supplied.')
