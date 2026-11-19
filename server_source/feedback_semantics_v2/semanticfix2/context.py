"""阶段由动作与子阶段共同确定，不把未知组合推成抓取。"""
from copy import deepcopy

PHASES = {
    ('move_to_grasp_pose','pregrasp'):('grasp_prepare','抓取前准备'),
    ('move_to_grasp_pose','approach'):('grasp_approach','接近待抓物体'),
    ('move_to_grasp_pose','grasp'):('grasp_pose','到达抓取姿态'),
    ('move_to_point','lift'):('carry_lift','抓取后的抬升'),
    ('move_to_point','transport'):('carry_transport','携物运输至放置目标上方'),
    ('move_to_point','descent'):('place_descent','携物下降至释放位姿，不是抓取前下降'),
    ('back_to_zero','retract'):('post_release_retract','释放后的回撤'),
    ('back_to_zero','return_home'):('return_home','返回初始姿态'),
}


def stage_context(diagnostics):
    action,segment = diagnostics.get('action'),diagnostics.get('motion_segment')
    phase,meaning = PHASES.get((action,segment),('unknown','阶段信息不足或动作组合未定义'))
    return dict(action=action,motion_segment=segment,phase=phase,meaning=meaning,
                source='deterministic_executor_semantics',version='motion-context-v1')


def enrich(report,*,attempt):
    value = deepcopy(report)
    evidence = value.setdefault('evidence',{})
    context = stage_context(evidence.get('diagnostics',{}))
    context['attempt'] = attempt
    evidence['motion_context'] = context
    evidence['contacts_semantics'] = 'contacts contains root categories; contact_details identifies actual contacting geometry and bodies'
    if 'contact_details' in evidence:
        evidence['contact_details'].update(attempt=attempt,motion_context=context)
    return value


def project(report,config,*,attempt):
    from recovery.feedback import project as previous_project
    value = previous_project(report,config,attempt=attempt)
    for field in ('motion_context','contacts_semantics','contact_details'):
        if field in report.get('evidence',{}):
            value['evidence'][field] = deepcopy(report['evidence'][field])
    return value
