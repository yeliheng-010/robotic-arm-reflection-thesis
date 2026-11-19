from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import mujoco
from cv_select import scene
from model_grasp_gpu_v1.planning import forbid
from surface_physical_v1.common import verify
from surface_grasp_v1.common import read,save,sha
import held_observation_v3.audit as audit
from held_observation_v3.worker import scope
import held_observation_review_v1.worker as previous
from held_observation_review_v1.compare import compare_saved,summarize_search,trace,PHASES

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
TRIAL=PROJECT/'held_observation_v3/trial'
SOURCE=TRIAL/'cases/964347/first'


@contextmanager
def observation_scene(config):
    with scene(config) as context:
        with patch.object(mujoco,'mj_step',forbid),patch.object(mujoco,'mj_step1',forbid), \
             patch.object(mujoco,'mj_step2',forbid):
            yield context


def main():
    verify(TRIAL/'manifest.json')
    verify(TRIAL/'execution_manifest.json')
    paths=[p for p in TRIAL.rglob('*') if p.is_file()]
    paths += [p for p in (PROJECT/'held_observation_review_v1').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts]
    identities={str(p):sha(p) for p in paths}
    sources={str(p):sha(p) for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')}
    save(ROOT/'manifest.json',dict(identities=identities,source_identities=sources,
        physical_attempts=0,model_calls=0,training_runs=0))
    with scope(),patch.object(audit,'compare_saved',compare_saved), \
         patch.object(audit,'scene',observation_scene),patch.object(previous,'scene',observation_scene):
        first=compare_saved(SOURCE/'checkpoints/after_lift',TRIAL/'replay/after_lift')
        second=audit.replay(SOURCE/'checkpoints/before_release',ROOT/'replay/before_release')
        cache=previous.cache_evidence()
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
