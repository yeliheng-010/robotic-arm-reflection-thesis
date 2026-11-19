"""已测动作的后果与未知动作分开，不把离线命中冒充物理成功。"""
import json


def canonical(action):
    return json.dumps(action, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':'))


def classify(action, outcomes, *, valid, completed=False):
    if not valid:
        return 'invalid_output'
    if action['id'] == 'STOP':
        return 'completed_stop' if completed else 'stop_before_completion'
    observed = {row['success'] for row in outcomes if row['action'] == action}
    if observed == {True}:
        return 'observed_success'
    if observed == {False}:
        return 'observed_failure'
    if observed == {True, False}:
        return 'mixed_observed_outcomes'
    return 'unmeasured_action'
