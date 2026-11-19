"""仅审计6851的claim前导入失败，不加载仿真或Open3D。"""
import ast
import base64
import importlib.metadata
import os
import sys
from pathlib import Path
from qualified_closure_dynamics_v3.protocol import (
    ROOT as ENGINE, RUN, read, save, sha, require, read_snapshot, verify_authorization)

ROOT = Path(__file__).resolve().parent
PREFIX = 'ValueError: New or changed imported file: '


def failure_binding(auth):
    log = ROOT / 'execute-6851.log'
    lines = log.read_text(encoding='utf-8').splitlines()
    errors = [line for line in lines if line.startswith(PREFIX)]
    require(len(errors) == 1, 'Unexpected execution failure')
    rejected = Path(errors[0][len(PREFIX):])
    require(rejected.name == 'pybind.cpython-311-x86_64-linux-gnu.so', 'Unexpected extension')
    require(rejected.parent.name == 'cuda' and rejected.parent.parent.name == 'open3d', 'Unexpected package')
    snapshot = read_snapshot()
    require(str(rejected) not in snapshot['files'], 'Rejected file was already registered')
    require(str(rejected) not in auth['identities'], 'Rejected binary was bound')
    cpu = rejected.parent.parent / 'cpu' / rejected.name
    require(str(cpu) in snapshot['files'], 'CPU extension was not prepared')
    distribution = importlib.metadata.distribution('open3d')
    record = next(item for item in distribution.files or []
                  if Path(distribution.locate_file(item)).resolve() == rejected)
    digest = sha(rejected)
    recorded = record.hash
    encoded = base64.urlsafe_b64encode(bytes.fromhex(digest)).decode().rstrip('=')
    matches = bool(recorded and recorded.mode == 'sha256' and recorded.value == encoded)
    require(matches, 'Current installation RECORD differs')
    source = rejected.parent.parent / '__init__.py'
    require(str(source) in auth['identities'], 'Import selector was not frozen')
    relevant = [dict(line=i, text=line) for i, line in enumerate(source.read_text().splitlines(), 1)
                if any(key in line for key in ('open3d_core_cuda_device_count',
                    'from open3d.cuda', 'from open3d.cpu', '__DEVICE_API__ ='))]
    return dict(rejected_file=str(rejected), rejected_sha256=digest,
        prepared_cpu_file=str(cpu), cpu_sha256=sha(cpu), selector_sha256=sha(source),
        selector_lines=relevant, package=distribution.metadata['Name'], version=distribution.version,
        installed_record_matches=matches, rejected_binary_previously_bound=False,
        log_sha256=sha(log))


def control_flow():
    source = ENGINE / 'entry.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    main_calls = {node.func.id: node.lineno for node in ast.walk(functions['main'])
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    require(main_calls['preclaim'] < main_calls['consume'] < main_calls['run_environment'], 'Order changed')
    guards = [node for node in ast.walk(functions['preclaim']) if isinstance(node, ast.With)]
    guard = next(node for node in guards if any(isinstance(item.context_expr, ast.Call)
                 and isinstance(item.context_expr.func, ast.Name)
                 and item.context_expr.func.id == 'zero_motion' for item in node.items))
    calls = {node.func.id: node.lineno for node in ast.walk(guard)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
    require('load_runtime' in calls and 'validate_runtime' in calls, 'Unguarded import validation')
    return dict(entry_sha256=sha(source), main_calls=main_calls, guarded_calls=calls,
        before_claim_and_environment=True, counters_persisted=False,
        step_count_basis='frozen_control_flow_and_exception_location_not_saved_runtime_counters')


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    save(ROOT / 'audit_attempt.json', dict(consumed=1, scope='preclaim_import_failure_only',
        job=os.environ['SLURM_JOB_ID'], source_sha256=sha(Path(__file__)),
        launcher_sha256=sha(ROOT / 'failure_audit.sbatch')))
    require(not RUN.exists(), 'Unexpected v3 run or claim')
    auth = verify_authorization(ENGINE / 'authorization.json')
    registration = read(ROOT / 'registration.json')
    require(registration['authorization_sha256'] == sha(ENGINE / 'authorization.json'), 'Authorization changed')
    for name, digest in registration['sources'].items():
        require(sha(name) == digest, 'Registered wrapper changed: ' + name)
    status = (ROOT / 'execution_status.txt').read_text()
    require('6851|FAILED|1:0|' in status, 'Execution not confirmed failed')
    detail, order = failure_binding(auth), control_flow()
    forbidden = ('mujoco', 'open3d', 'grasp_process')
    require(not any(name == key or name.startswith(key + '.') for name in sys.modules
                    for key in forbidden), 'Runtime imported in failure audit')
    files = [ENGINE / 'authorization.json', ROOT / 'registration.json', ROOT / 'execution_status.txt',
             ROOT / 'execute-6851.log', ENGINE / 'preflight.sbatch', ROOT / 'execute.sbatch']
    result = dict(passed=True, scope='preclaim_import_failure_evidence_only',
        job=os.environ['SLURM_JOB_ID'], execution_job='6851', execution_failed=True,
        verified_identities=len(auth['identities']), new_claim_consumed=0, run_absent=True,
        setup_steps=0, task_steps=0, integration_count_basis=order['step_count_basis'],
        counters_persisted=False, audit_integration_steps=0, simulation_imported=False,
        model_calls=0, training_runs=0, dynamics_validated=False, production_ready=False,
        retry_allowed=False, failure_reason='cpu_preparation_did_not_cover_gpu_open3d_import',
        dependency=detail, control_flow=order, identities={str(p): sha(p) for p in files})
    save(ROOT / 'failure_audit.json', result)
    print({key: result[key] for key in ('passed', 'scope', 'verified_identities',
          'new_claim_consumed', 'setup_steps', 'task_steps', 'dynamics_validated')}, flush=True)


if __name__ == '__main__':
    main()
