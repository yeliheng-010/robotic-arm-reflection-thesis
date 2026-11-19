"""只读审计场景创建前失败；不导入MuJoCo、不重试诊断。"""
import ast
import base64
import hashlib
import importlib.metadata
import os
import sys
import sysconfig
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import ROOT as ENGINE, PROJECT, read, save, sha, require

ROOT = Path(__file__).resolve().parent


def provenance(path):
    libraries = {name: str(Path(value).resolve()) for name, value in sysconfig.get_paths().items()
                 if name in ('purelib', 'platlib')}
    inside = any(path.is_relative_to(Path(value)) for value in libraries.values())
    require(inside, 'Unexpected dependency location; review rather than assume')
    distribution = importlib.metadata.distribution('setuptools')
    record = next(item for item in distribution.files or []
                  if Path(distribution.locate_file(item)).resolve() == path)
    recorded = record.hash
    actual = base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).decode().rstrip('=')
    return dict(path=str(path), sha256=sha(path), library_roots=libraries,
                within_project=path.is_relative_to(PROJECT), within_python_library=inside,
                distribution='setuptools', version=distribution.version,
                record_hash_mode=recorded.mode if recorded else None,
                installed_record_matches=bool(recorded and recorded.mode == 'sha256' and recorded.value == actual))


def source_order():
    source = ENGINE / 'entry.py'
    tree = ast.parse(source.read_text(encoding='utf-8'))
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                    and node.name == 'run_environment')
    calls = [(node.func.id, node.lineno) for node in ast.walk(function)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
    imports_line = next(line for name, line in calls if name == 'imported_sources')
    opened_line = next(line for name, line in calls if name == 'opened')
    require(imports_line < opened_line, 'Unexpected execution ordering')
    return dict(source_sha256=sha(source), imported_sources_line=imports_line,
                environment_open_line=opened_line, failure_precedes_environment=True)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    save(ROOT / 'audit_claim.json', dict(consumed=1, scope='pre_scene_failure_evidence',
                                       job=os.environ['SLURM_JOB_ID']))
    run = ENGINE / 'run'
    require({p.name for p in run.iterdir()} == {'claim.json', 'failure.json'}, 'Unexpected run artifacts')
    claim, failure = read(run / 'claim.json'), read(run / 'failure.json')
    auth = read(ENGINE / 'authorization.json')
    require(claim['consumed'] == 1 and claim['job'] == '6832', 'Claim mismatch')
    require(claim['authorization_sha256'] == sha(ENGINE / 'authorization.json'), 'Authorization changed')
    require(failure['setup_step_requests'] == failure['task_step_requests'] == 0, 'Unexpected integration')
    prefix = 'ValueError: Unbound runtime source: '
    require(failure['error'].startswith(prefix), 'Unexpected failure')
    dependency = Path(failure['error'][len(prefix):]).resolve()
    require(str(dependency) not in auth['identities'], 'Dependency was actually bound')
    for name, digest in auth['identities'].items():
        require(sha(name) == digest, 'Frozen input changed: ' + name)
    detail, order = provenance(dependency), source_order()
    require(detail['installed_record_matches'], 'Installed dependency RECORD mismatch')
    require(not any(name == 'mujoco' or name.startswith('mujoco.') for name in sys.modules), 'Simulation imported')
    files = [ENGINE / 'authorization.json', run / 'claim.json', run / 'failure.json',
             ROOT / 'execute-6832.log', ROOT / 'registration.json']
    result = dict(passed=True, scope='pre_scene_failure_evidence_only', original_execution_failed=True,
        dynamics_validated=False, setup_steps=0, task_steps=0, audit_integration_steps=0,
        consumed_diagnostic_claim=1, frozen_identities=len(auth['identities']),
        provenance=detail, source_order=order, historical_dependency_hash_bound=False,
        failure_reason='project_directory_check_includes_nested_python_site_packages',
        identities={str(p): sha(p) for p in files}, audit_source_sha256=sha(Path(__file__)),
        no_simulation_imported=True, job=os.environ['SLURM_JOB_ID'])
    save(ROOT / 'failure_audit.json', result)
    print(dict(passed=True, scope=result['scope'], dynamics_validated=False,
               verified_identities=result['frozen_identities'], setup_steps=0, task_steps=0), flush=True)


if __name__ == '__main__':
    main()
