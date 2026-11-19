from qualified_joint_feedback_v1.inputs import context
from qualified_joint_feedback_v1.inputs import history as previous_history
from qualified_closure_feedback_v1.common import PROJECT, SEED, read
from qualified_closure_feedback_v1.policy import entry


def history():
    rows = previous_history(SEED)
    old = PROJECT / f'qualified_joint_feedback_v1/run/{SEED}/decision_1'
    rows.append(entry(read(old / 'validated.json')['action'], 'gripper_closure'))
    return rows
