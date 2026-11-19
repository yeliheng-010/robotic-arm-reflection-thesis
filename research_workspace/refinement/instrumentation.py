"""单进程实验遥测：观察原实现，不更改检测阈值、轨迹或异常。"""
from contextlib import contextmanager, ExitStack
from functools import wraps
from unittest.mock import patch

DEFAULT_COLLISION_THRESHOLD = 0.05
SEGMENTS = {'move_to_grasp_pose': ('pregrasp', 'approach', 'grasp'),
            'move_to_point': ('lift', 'transport', 'descent'),
            'back_to_zero': ('retract', 'return_home')}


def filter_evidence(collision, empty, *, ious, scene_points, threshold):
    if len(collision) != len(empty):
        raise ValueError('Collision and empty masks must have equal length')
    return {'candidate_count': len(collision), 'collision_rejected': sum(map(bool, collision)),
            'empty_rejected': sum(map(bool, empty)),
            'surviving_count': sum(not (c or e) for c, e in zip(collision, empty)),
            'collision_iou': [float(v) for v in ious[0]],
            'collision_threshold': float(threshold), 'scene_point_count': int(scene_points),
            'signal_source': 'observed_point_cloud_filter'}


class TracedPlanner:
    def __init__(self, planner, *, state, segment):
        self.planner, self.state, self.segment = planner, state, segment

    def interpolate(self, time):
        self.state['motion_segment'] = self.segment
        self.state.pop('commanded_tcp_xyz', None)
        pose = self.planner.interpolate(time)
        if hasattr(pose, 't'):
            self.state['commanded_tcp_xyz'] = pose.t.tolist()
        else:
            self.state.pop('commanded_tcp_xyz', None)
        return pose

    def __getattr__(self, name):
        return getattr(self.planner, name)


def observe_detection(original, state):
    @wraps(original)
    def detect(detector, grasps, **kwargs):
        result = original(detector, grasps, **kwargs)
        detail_args = dict(kwargs, return_empty_grasp=True, return_ious=True)
        collision, empty, ious = original(detector, grasps, **detail_args)
        state['grasp_filter'] = filter_evidence(collision, empty, ious=ious,
            scene_points=len(detector.scene_points),
            threshold=kwargs.get('collision_thresh', DEFAULT_COLLISION_THRESHOLD))
        return result
    return detect


def observe_action(original, name, state):
    @wraps(original)
    def action(flow, *args, **kwargs):
        state['action'] = name
        state['planner_calls'] = 0
        return original(flow, *args, **kwargs)
    return action


def observe_planners(original, state):
    @wraps(original)
    def run(*args, **kwargs):
        values = list(args)
        planners = values[2] if len(values) > 2 else kwargs['planner_array']
        names = SEGMENTS.get(state.get('action'), ('unknown',))
        start = state.get('planner_calls', 0)
        traced = [TracedPlanner(p, state=state, segment=names[min(start+i, len(names)-1)])
                  for i, p in enumerate(planners)]
        state['planner_calls'] = start + len(planners)
        if len(values) > 2:
            values[2] = traced
        else:
            kwargs['planner_array'] = traced
        return original(*values, **kwargs)
    return run


def contact_bounds(monitor, report):
    from reflection.monitors import object_extents
    env = monitor.env
    bodies = {name for pair in report.evidence.get('contacts', []) for name in pair}
    bounds = []
    for name in sorted(bodies):
        try:
            body = env.mj_model.body(name)
            if body.geomnum == 0:
                continue
            low, high = object_extents(env.mj_model, env.mj_data, body.id)
            bounds.append({'body': name, 'lower_xyz': low.tolist(), 'upper_xyz': high.tolist()})
        except (KeyError, ValueError, IndexError):
            continue
    return bounds


def observe_monitor(original, state):
    @wraps(original)
    def tick(monitor):
        from reflection.errors import TaskAbort
        try:
            return original(monitor)
        except TaskAbort as exc:
            state['contact_bounds_world'] = contact_bounds(monitor, exc.report)
            raise
    return tick


def diagnostic_snapshot(state, report):
    evidence = {k: v for k, v in state.items() if k != 'planner_calls'}
    if report is not None:
        evidence['failure_stage'] = report.stage
    if report is not None and report.stage == 'placement':
        evidence['observation_phase'] = 'post_execution_evaluation'
        evidence['last_completed_motion'] = {
            key: evidence.pop(key) for key in
            ('action', 'motion_segment', 'commanded_tcp_xyz') if key in evidence}
    return evidence


@contextmanager
def capture(state):
    import grasp_process as grasp
    from reflection.monitors import ExecutionMonitor
    with ExitStack() as stack:
        detector = grasp.ModelFreeCollisionDetector
        stack.enter_context(patch.object(detector, 'detect', observe_detection(detector.detect, state)))
        stack.enter_context(patch.object(grasp, '_run_planners', observe_planners(grasp._run_planners, state)))
        stack.enter_context(patch.object(ExecutionMonitor, 'tick', observe_monitor(ExecutionMonitor.tick, state)))
        for name in SEGMENTS:
            original = getattr(grasp.GraspFlow, name)
            stack.enter_context(patch.object(grasp.GraspFlow, name, observe_action(original, name, state)))
        yield
