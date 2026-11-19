"""核验状态、同种子初态、物理成功和原选择回放。"""
from pathlib import Path
from rc_audit import check_step
from cd_common import ROOT, LAYOUT, read


def outcome(step):
    feedback = step['feedback'] or {}
    return dict(success=step['success'],error=feedback.get('error_type'),
        phase=feedback.get('evidence',{}).get('motion_context',{}).get('phase'))


def audit_result(result, branch, manifest):
    case = manifest['cases'][branch['case_index']]
    assert result['branch'] == branch and result['status'] == 'completed'
    assert not result['test_used'] and not result['training_approved']
    assert result['extra_observations'] == 0
    step = result['step']
    assert step['index'] == 3 and step['state'] == branch['action']['state']
    folder = ROOT/'tasks'/f"{branch['index']:03d}"
    assert Path(step['result_path']) == folder/'attempt_3/result.json'
    assert set(folder.rglob('result.json')) == {folder/'result.json',Path(step['result_path'])}
    check_step(step,case['source'],read(LAYOUT/'plan.json'))
    checks = []
    for name in ('rule','model'):
        if branch['action']['id'] == case[name+'_action']['id']:
            assert outcome(step) == outcome(case[name+'_final']), 'Physical replay changed'
            checks.append(name)
    return dict(passed=True,index=branch['index'],case_id=case['id'],
        origin=branch['origin'],action_id=branch['action']['id'],outcome=outcome(step),replays=checks)
