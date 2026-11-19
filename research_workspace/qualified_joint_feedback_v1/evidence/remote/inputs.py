from qualified_joint_feedback_v1.common import PROJECT, read
from qualified_joint_feedback_v1.policy import entry, outcome


def history(seed):
    previous = PROJECT/f'qualified_intent_v1/run_v3/{seed}'
    action = read(previous/'validated.json')['action']
    if seed == 978501:
        result = read(PROJECT/f'qualified_path_v1/run/planning/{seed}/private_result.json')
        return [entry(action, outcome(result)['stage'])]
    rows = [entry(action, 'grasp_endpoint')]
    source = PROJECT/'qualified_feedback_v1/run'
    for record in read(source/'result.json')['rows']:
        assert record['status'] == 'rejected'
        folder = source/f"decision_{record['ordinal']}"
        rows.append(entry(read(folder/'validated.json')['action'], 'grasp_endpoint'))
    return rows


def context(seed):
    source = PROJECT/f'qualified_model_v1/run/{seed}'
    request = read(source/'request.json')
    parsed = read(source/'validated.json')['parsed']
    grounding = dict(task=request['messages'][1]['content'],
        source_pixel=parsed['source_pixel'], destination_pixel=parsed['destination_pixel'],
        pixel_units='0_to_1000_normalized_model_predictions')
    return dict(original=read(PROJECT/f'qualified_intent_v1/run_v3/{seed}/request.json'),
        geometry=read(PROJECT/f'qualified_path_v1/run/goals/{seed}/geometry.json'),
        grounding=grounding)
