import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import held_observation_v1.common as common
import held_observation_v1.worker as worker
import held_observation_v1.audit as original_audit
import held_observation_v2.worker as previous_worker
from held_observation_v1.common import PROJECT,read,save,sha,verify
from held_observation_v3.audit import compare_saved,replay
from held_observation_v3.policy import assess

ROOT=Path(__file__).resolve().parent
TRIAL=ROOT/'trial'
PREVIOUS=PROJECT/'held_observation_v2/trial'


def prepare():
    assert not TRIAL.exists()
    old=verify(PREVIOUS/'manifest.json')
    identities=dict(old['identities'])
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')]
    paths+=[p for p in PREVIOUS.rglob('*') if p.is_file()]
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'manifest.json',dict(old,identities=identities,
        preflight_scope='observation_only_no_release',control_ready=False,
        revision='Per-file RGB integrity plus existing pixel tolerance; separate capture readiness'))


def preflight():
    verify(TRIAL/'manifest.json')
    folder=PREVIOUS/'preflight'
    assert read(folder/'bridge.json')['planners']==[]
    assert read(folder/'strict_held_precheck.json')['passed']
    assert read(folder/'lifecycle.json')['actual_close_calls']==1
    original=read(PREVIOUS/'preflight_result.json')
    assert original['physical_attempts']==0
    result=compare_saved(folder/'checkpoints/preflight',PREVIOUS/'replay/preflight')
    decision=assess(original['observation'],result)
    record=dict(passed=decision['capture_ready'],scope='observation_only_no_release',
        physical_attempts=0,source_job=6490,decision=decision,observation=original['observation'])
    save(TRIAL/'preflight_result.json',record)
    save(TRIAL/'preflight_audit.json',dict(record,independent=True,audit_verified=True,
        replay=result,reused_independent_process_evidence=True))
    print(record,flush=True)


def register():
    previous=verify(TRIAL/'manifest.json')
    for name in ('preflight_result.json','preflight_audit.json'):
        result=read(TRIAL/name)
        assert result['passed'] and result['scope']=='observation_only_no_release'
        assert not result['decision']['control_ready'] and not result['decision']['release_authorized']
    identities=dict(previous['identities'])
    paths=[TRIAL/name for name in ('manifest.json','preflight_result.json','preflight_audit.json')]
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'execution_manifest.json',dict(identities=identities,max_physical_attempts=1,
        release_allowed=False,control_ready=False,model_calls=0,training_runs=0))


@contextmanager
def scope():
    with previous_worker.scope(),patch.object(common,'TRIAL',TRIAL), \
         patch.object(worker,'TRIAL',TRIAL),patch.object(original_audit,'TRIAL',TRIAL), \
         patch.object(original_audit,'replay',replay):
        yield


if __name__=='__main__':
    actions=dict(prepare=prepare,preflight=preflight,register=register,
                 execute=worker.execute,audit_physical=original_audit.physical)
    with scope():
        actions[sys.argv[1]]()
