"""仅核验本地方案及归档绑定，不导入仿真、模型或执行入口。"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
ARCHIVE = 'qualified_closure_reachability_v1/evidence/remote/run/'
PREFLIGHT = 'qualified_checkpoint_preflight_v1/evidence/remote/run/preflight/'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_bindings(protocol):
    for name, digest in protocol['local_sha256'].items():
        path = (PROJECT / name).resolve()
        require(path.is_relative_to(PROJECT), 'source outside project')
        require(sha(path) == digest, 'changed source: ' + name)
    manifest = read(PROJECT / ARCHIVE / 'manifest.json')
    initial = protocol['remote_initial_state']
    require(manifest['identities'][initial['path']] == initial['sha256'], 'initial binding')
    require(initial['verified_live_this_turn'] is False, 'remote verification overclaim')
    inputs = read(PROJECT / ARCHIVE / 'input.json')
    closure = read(PROJECT / PREFLIGHT / 'closure.json')
    require(protocol['arm_command'] == inputs['command'] == closure['command'], 'command')
    require(inputs['parent_closure_sha256'] == sha(PROJECT / PREFLIGHT / 'closure.json'), 'parent')
    require(len(inputs['configurations']) == 5, 'saved configurations')
    plan = read(PROJECT / PREFLIGHT / 'private_plan.json')['plan']
    require(protocol['arm_command'] != plan['selected']['q1'], 'prepose used as closure')


def check_scope(protocol):
    require(protocol['status'] == 'proposed_not_authorized', 'status')
    require(protocol['execution_authorized'] is False, 'authorization')
    require(all(v == 0 for v in protocol['actual_this_turn'].values()), 'execution occurred')
    budget = protocol['proposed_budget']
    require(budget == dict(trajectories=1, setup_steps=500, task_steps=1000,
                          model_calls=0, full_task_attempts=0, training_runs=0,
                          zero_integration_audits=1, job_wall_seconds=600,
                          loop_wall_seconds=120), 'budget')
    controls = read(PROJECT / ARCHIVE / 'controls.json')
    command, sequence = 0.0, []
    for _ in range(budget['task_steps']):
        command = min(command + 0.2, 255)
        sequence.append(command)
    require(sequence == controls['control_commands'], 'native control sequence')
    require(command == controls['last_command'], 'last control')
    require(protocol['safety_gate_changed'] is False, 'safety gate')
    allowed = {'PLAN.md', 'protocol.proposed.json', 'verify_plan.py', 'evidence'}
    require({p.name for p in ROOT.iterdir()} <= allowed, 'unexpected run artifact')
    return command


def main():
    protocol = read(ROOT / 'protocol.proposed.json')
    check_bindings(protocol)
    last = check_scope(protocol)
    result = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                  scope='local_archive_and_plan_consistency_only',
                  bound_local_files=len(protocol['local_sha256']),
                  server_live_reverified=False, native_command_count=1000,
                  last_command=last, actual_this_turn=protocol['actual_this_turn'],
                  execution_authorized=False, dynamics_validated=False,
                  artifacts={name: sha(ROOT / name) for name in
                             ('PLAN.md', 'protocol.proposed.json', 'verify_plan.py')})
    folder = ROOT / 'evidence'
    folder.mkdir(exist_ok=True)
    with (folder / 'PLAN_VERIFICATION.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
