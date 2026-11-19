from pathlib import Path
from unittest.mock import patch
import mujoco
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
from cv_select import scene
from model_grasp_gpu_v1.planning import forbid
from surface_physical_v1.common import verify
from surface_grasp_v1.common import read,save,sha
import held_observation_v3.audit as audit
from held_observation_v3.worker import scope
from held_observation_review_v1.compare import compare_saved,summarize_search,trace,contact_rows,PHASES

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
TRIAL=PROJECT/'held_observation_v3/trial'
SOURCE=TRIAL/'cases/964347/first'


def cache_evidence():
    folder=SOURCE/'checkpoints/before_release'
    snapshot=read(folder/'snapshot.json')
    with scene(snapshot['case']['config']) as (env,unused):
        with np.load(folder/'state.npz') as data:
            mujoco.mj_setState(env.mj_model,env.mj_data,data['state'],mujoco.mjtState.mjSTATE_INTEGRATION)
        mujoco.mj_forward(env.mj_model,env.mj_data)
        source=env.mj_data.body(snapshot['case']['item']['source']).xpos.copy()
    rows=contact_rows(SOURCE)
    error=np.linalg.norm(source-rows[-1]['source'])
    return dict(forward_center_world_m=source.tolist(),recorded_end_center_matches=bool(error==0.),
        end_center_error_m=float(error),previous_sample_same_time=rows[-2]['time']==rows[-1]['time'],
        previous_sample_center_delta_m=float(np.linalg.norm(source-rows[-2]['source'])))


def main():
    verify(TRIAL/'manifest.json')
    verify(TRIAL/'execution_manifest.json')
    paths=[p for p in TRIAL.rglob('*') if p.is_file()]
    identities={str(p):sha(p) for p in paths}
    save(ROOT/'manifest.json',dict(identities=identities,
        source_identities={str(p):sha(p) for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')},
        physical_attempts=0,model_calls=0,training_runs=0))
    with scope(),patch.object(audit,'compare_saved',compare_saved), \
         patch.object(mujoco,'mj_step',forbid),patch.object(mujoco,'mj_step1',forbid), \
         patch.object(mujoco,'mj_step2',forbid):
        first=compare_saved(SOURCE/'checkpoints/after_lift',TRIAL/'replay/after_lift')
        second=audit.replay(SOURCE/'checkpoints/before_release',ROOT/'replay/before_release')
        cache=cache_evidence()
    old=PROJECT/'surface_physical_v1/trial/cases/964347/first'
    result=dict(review_completed=True,strict_observation_audit_passed=False,
        phases=dict(after_lift=first,before_release=second),trace=trace(SOURCE,old),cache=cache,
        coverage={phase:summarize_search(SOURCE/'checkpoints'/phase) for phase in PHASES},
        outcome=read(TRIAL/'outcome.json'),guard=read(SOURCE/'guard.json'),
        lifecycle=read(SOURCE/'lifecycle.json'),additional_physical_attempts=0,control_ready=False,
        training_eligible=False,inputs_unchanged=all(sha(p)==digest for p,digest in identities.items()))
    assert result['inputs_unchanged']
    save(ROOT/'review.json',result)
    print(result,flush=True)


if __name__=='__main__':
    main()
