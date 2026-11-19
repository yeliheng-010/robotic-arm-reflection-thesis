"""独立进程只复核保存状态，绝不重放动力学。"""
import os
import sys
from qualified_closure_mjb_v1.protocol import (
    PROJECT, RUN, VERIFIED, proposal, read, save, sha, require, verify_sources)


def audit_folder(folder, *, verification):
    from qualified_closure_mjb_v1.runtime import checked_imports
    imports = checked_imports()
    for name, digest in read(folder/'primary_inventory.json').items():
        require(sha(folder/name) == digest, 'Changed trajectory evidence: '+name)
    require(read(folder/'claim.json')['kind'] == 'entry_verification' if verification else
            read(folder/'claim.json')['diagnostic_id'] == 'qualified_closure_mjb_v1-978505', 'Wrong claim')
    save(folder/'audit_claim.json', dict(consumed=1, job=os.environ['SLURM_JOB_ID'], integration_budget=0))
    from qualified_closure_mjb_v1.resources import guarded
    from qualified_closure_mjb_v1.restore import load_model, model_identity
    from qualified_closure_mjb_v1.trace import trace_contract
    from qualified_closure_mjb_v1.audit_states import audit_states
    from qualified_scene_candidate_v1.common import loaded_sources
    with guarded() as resources:
        try:
            model = load_model(resources)
            metadata = read(folder/'metadata.json')
            require(model_identity(model) == metadata['model_fields'], 'Metadata model identity differs')
            require(metadata['model_sha256'] == proposal()['model']['sha256'], 'Metadata MJB differs')
            count = trace_contract(folder, allow_verification=verification)
            minimum = audit_states(folder, model, metadata=metadata, count=count)
            model_identity(model)
            identities = verify_sources()
            loaded = loaded_sources(identities)
            require(resources.gate.requests == resources.gate.returns == 0, 'Audit integration requested')
            save(folder/'audit_loaded_sources.json', loaded)
            save(folder/'audit_result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'], task_steps=count,
                counts=resources.summary(), import_counts=imports['counts'], verified_identities=len(identities),
                minimum_reference_distance_rad=minimum, cross_timing_equality_required=False,
                verification_only=verification, production_ready=False, dynamics_validated=False))
        except Exception as error:
            save(folder/'audit_failure.json', dict(error=type(error).__name__+': '+str(error),
                 counts=resources.summary()))
            raise


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    require(sys.argv[1:] in ([], ['--verify']), 'Unknown audit arguments')
    verification = sys.argv[1:] == ['--verify']
    audit_folder(VERIFIED if verification else RUN, verification=verification)


if __name__ == '__main__':
    main()
