"""独立授权与一次claim；此模块不能发放授权。"""
import hashlib
import json
import os
from pathlib import Path

DIAGNOSTIC_ID = 'qualified_closure_dynamics_v1-978505'
BUDGET = dict(trajectories=1, setup_steps=500, task_steps=1000, model_calls=0,
              full_task_attempts=0, training_runs=0, zero_integration_audits=1,
              job_wall_seconds=600, loop_wall_seconds=120)
ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RUN = ROOT / 'run'
HASH_CHUNK_BYTES = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(HASH_CHUNK_BYTES), b''):
            digest.update(chunk)
    return digest.hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def commands():
    value, rows = 0.0, []
    for _ in range(BUDGET['task_steps']):
        value = min(value + 0.2, 255.0)
        rows.append(value)
    return rows


def verify(auth):
    require(auth.get('execution_authorized') is True, 'Dynamics not authorized')
    require(auth.get('diagnostic_id') == DIAGNOSTIC_ID, 'Wrong diagnostic')
    require(auth.get('budget') == BUDGET, 'Wrong budget')
    require(all(type(value) is int for value in auth['budget'].values()), 'Budget must use integers')
    require(bool(auth.get('approval_reference')), 'Missing user approval reference')
    require(bool(auth.get('identities')), 'Empty identities')
    for name, digest in auth['identities'].items():
        require(sha(name) == digest, 'Changed frozen source: ' + name)


def claim(authorization, folder):
    auth = read(authorization)
    verify(auth)
    save(Path(folder) / 'claim.json', dict(consumed=1, diagnostic_id=DIAGNOSTIC_ID,
         authorization_sha256=sha(authorization), job=os.environ.get('SLURM_JOB_ID')))
    return auth


def inventory(folder):
    return {path.name: sha(path) for path in folder.iterdir() if path.is_file()}
