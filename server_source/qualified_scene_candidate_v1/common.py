"""固定来源与完整运行模块的文件指纹。"""
import os
import sys
from pathlib import Path
from qualified_initial_projection_run_v2.protocol import verify as verify_parent
from qualified_closure_dynamics_v1.protocol import read, save, sha, require

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
PARENT = PROJECT / 'qualified_initial_projection_run_v2'
CANDIDATE = PARENT / 'run/candidate_state.npz'
CANDIDATE_SHA = 'f36b22f5fef62ce9d66feb0c9de61a0905a890e5c669a4744bdc60a55c808596'


def verify():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    identities = dict(verify_parent())
    for folder in ('qualified_projection_diagnostic_v1', 'qualified_initial_projection_v2',
                   'qualified_initial_projection_run_v2', ROOT.name):
        for name, digest in read(PROJECT / folder / 'BINDINGS.json').items():
            require(sha(PROJECT / name) == digest, 'Changed source: '+name)
            identities[str(PROJECT / name)] = digest
    require(sha(CANDIDATE) == CANDIDATE_SHA, 'Wrong candidate')
    audit = read(PARENT / 'run/audit_result.json')
    require(audit['candidate_verified'] and audit['candidate_sha256'] == CANDIDATE_SHA, 'Candidate not verified')
    return identities


def loaded_sources(identities):
    files, unbound = {}, []
    for module in list(sys.modules.values()):
        raw = getattr(module, '__file__', None)
        if not isinstance(raw, str):
            continue
        path = Path(raw)
        if not path.is_file() or not path.resolve().is_relative_to(PROJECT):
            continue
        name = str(path) if str(path) in identities else str(path.resolve())
        if name not in identities:
            unbound.append(name)
            continue
        files[name] = sha(path)
        require(files[name] == identities[name], 'Loaded source changed: '+name)
    require(not unbound, 'Unbound imported files: '+str(sorted(set(unbound))))
    return files


def claim(folder, name):
    save(Path(folder) / (name+'_claim.json'), dict(consumed=1, job=os.environ['SLURM_JOB_ID'],
        candidate_sha256=CANDIDATE_SHA, initialization_budget=0, integration_budget=0))
