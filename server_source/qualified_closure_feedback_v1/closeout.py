"""核验反馈已送达、预算已耗尽且未开启物理执行。"""
import ast
import json
import os
import subprocess
from qualified_closure_feedback_v1.common import ROOT, PROJECT, RUN, read, save, sha, verify


def findings():
    summary = read(RUN / 'result.json')
    assert read(RUN / 'audit_result.json')['passed']
    assert summary['model_reservations'] == summary['generations_started'] == summary['responses_saved'] == 2
    assert summary['ready_ordinal'] is None and summary['physical_attempts'] == 0
    assert not (RUN / 'execution_manifest.json').exists() and not (RUN / 'physical').exists()
    first, second = [RUN / f'decision_{i}' for i in (1, 2)]
    actions = [read(p / 'validated.json')['action'] for p in (first, second)]
    requests = [read(p / 'request.json') for p in (first, second)]
    bodies = [json.loads(r['messages'][1]['content']) for r in requests]
    assert actions[0] == actions[1]
    assert bodies[1]['history'][-1] == dict(action=actions[0], feedback=dict(status='rejected', stage='grasp_endpoint'))
    assert bodies[1]['history'][:-1] == bodies[0]['history']
    assert requests[0]['image'] == requests[1]['image']
    assert requests[0]['messages'][0] == requests[1]['messages'][0]
    assert bodies[0]['observation'] == bodies[1]['observation']
    assert bodies[0]['actions'] == bodies[1]['actions']
    assert [b['budget']['decisions'] for b in bodies] == [2, 1]
    planned = read(first / 'private_plan.json')
    endpoints = planned['plan']['endpoints']
    assert len(endpoints['grasps']) == 8 and not any(r['ok'] for r in endpoints['grasps'])
    assert planned['state_check']['passed']
    assert not (second / 'proposal.json').exists() and not (second / 'private_plan.json').exists()
    responses = [read(p / 'response.json') for p in (first, second)]
    assert all(r['finish_reason'] == 'stop' and r['identity']['adapter_enabled'] is False for r in responses)
    return dict(model_calls=2, action=actions[0], input_tokens=[r['prompt_tokens'] for r in responses],
         completion_tokens=[r['completion_tokens'] for r in responses], feedback_delivered=True,
         repeated_action_rejected_before_planning=True, first_grasp_endpoints_passed=0,
         first_grasp_endpoints_total=8, observation_and_action_range_unchanged=True,
         physical_registered=False, physical_attempts=0, training_runs=0,
         new_closure_gate_reached=False, state_check=planned['state_check'])


def main():
    manifest = verify()
    result = findings()
    old = PROJECT / 'qualified_execution_v1/run/attempt_claim.json'
    assert read(old)['consumed'] == 1
    files = list(ROOT.glob('*.py'))
    for path in files:
        content = path.read_text(encoding='utf-8')
        assert len(content.splitlines()) <= 300, path
        for node in ast.walk(ast.parse(content)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
    jobs = subprocess.run(['sacct', '-j', '6803,6804,6805,6806',
                          '--format=JobID,State,ExitCode,Elapsed', '-n', '-P'],
                         capture_output=True, check=True, text=True).stdout
    active = 'closeout-' + os.environ['SLURM_JOB_ID'] + '.log'
    identities = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.name != active}
    save(RUN / 'delivery_inventory.json', dict(passed=True, findings=result, identities=identities,
         frozen_identities=len(manifest['identities']), python_sources_checked=len(files), job_accounting=jobs,
         original_claim_sha256=sha(old), generator_source_sha256=sha(PROJECT / 'ai_diagnosis_failure_v1/f_generator.py')))
    print(dict(passed=True, findings=result, files=len(identities), job_accounting=jobs), flush=True)


if __name__ == '__main__':
    main()
