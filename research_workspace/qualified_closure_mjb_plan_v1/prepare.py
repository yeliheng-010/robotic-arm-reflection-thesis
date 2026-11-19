"""Slurm零构造/零积分方案核验；没有执行入口或轨迹授权。"""
import os
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
from qualified_closure_dynamics_v1.protocol import read, save, sha, require
from qualified_closure_dynamics_v3.guarded_imports import zero_motion, blocker

ROOT = Path(__file__).resolve().parent
PREPARED = ROOT / 'preparation'


def prevent_runtime(stack, counts):
    import mujoco
    import grasp_process
    from scipy import optimize
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    targets = ((mujoco, 'mj_forward', 'forward'), (mujoco.Renderer, 'render', 'rendering'),
               (UR5GraspEnv, 'reset', 'reset'), (UR5GraspEnv, 'step', 'environment_step'),
               (grasp_process.GraspFlow, 'close_gripper', 'close'),
               (grasp_process, '_run_planners', 'planning'),
               (optimize, 'minimize', 'optimizer'), (optimize, 'least_squares', 'optimizer'))
    for owner, name, label in targets:
        counts[label] = 0
        stack.enter_context(patch.object(owner, name, blocker(counts, label)))


def execute(counts, stack):
    from qualified_closure_mjb_plan_v1 import validate
    from qualified_scene_candidate_v1.common import loaded_sources
    prevent_runtime(stack, counts)
    identities, records = validate.sources()
    plan = read(ROOT / 'protocol.proposed.json')
    validate.protocol_check(plan)
    evidence = validate.evidence_check(plan)
    control = validate.control_check(plan)
    semantics = validate.semantics_check(plan)
    loaded = loaded_sources(identities)
    validate.sources()
    validate.protocol_check(plan)
    require(not any(counts.values()), 'Unexpected simulation request')
    save(PREPARED / 'loaded_sources.json', loaded)
    return dict(passed=True, plan_validated=True, execution_authorized=False, entrypoint_ready=False,
                dynamics_budget_consumed=0, verified_identities=len(identities),
                record_verification=records, evidence=evidence, control=control, semantics=semantics,
                proposed_budget=plan['proposed_budget'], production_ready=False, dynamics_validated=False)


def main():
    require(bool(os.environ.get('SLURM_JOB_ID')), 'Slurm required')
    save(PREPARED / 'claim.json', dict(kind='plan_verification', consumed=1,
         dynamics_budget_consumed=0, job=os.environ['SLURM_JOB_ID']))
    with zero_motion() as counts, ExitStack() as stack:
        try:
            result = execute(counts, stack)
            save(PREPARED / 'result.json', dict(job=os.environ['SLURM_JOB_ID'], counts=counts,
                bindings_sha256=sha(ROOT / 'BINDINGS.json'), protocol_sha256=sha(ROOT / 'protocol.proposed.json'),
                **result))
        except Exception as error:
            save(PREPARED / 'failure.json', dict(error=type(error).__name__+': '+str(error), counts=counts))
            raise
    save(PREPARED / 'inventory.json', {p.name: sha(p) for p in PREPARED.iterdir() if p.is_file()})
    print(dict(**result, counts=counts), flush=True)


if __name__ == '__main__':
    main()
