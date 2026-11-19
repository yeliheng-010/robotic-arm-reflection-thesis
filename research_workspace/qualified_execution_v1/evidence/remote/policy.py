"""观察发布与固定动作执行分离；不批准使用不合格帧重规划。"""


def initial_allowed(*, initial_qualified, state_matches, preflight_passed, audit_passed):
    return all(v is True for v in (initial_qualified, state_matches, preflight_passed, audit_passed))


def observation_action(*, requested, qualified):
    if not requested:
        return 'no_model_observation'
    return 'publish_qualified' if qualified is True else 'stop_without_model_input'


def accepted(*, completed, physical_placement, safety_error):
    return completed is True and physical_placement is True and safety_error is None
