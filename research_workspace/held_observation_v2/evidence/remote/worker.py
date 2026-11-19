import sys
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import held_observation_v1.common as common
import held_observation_v1.worker as worker
import held_observation_v1.register as register
import held_observation_v1.audit as audit
import held_observation_v1.runtime as runtime
import held_observation_v1.views as views
from held_observation_v1.common import PROJECT,read,save,sha,verify
from held_observation_v2.capture import checkpoint
from held_observation_v2.cameras import proposals

ROOT=Path(__file__).resolve().parent
TRIAL=ROOT/'trial'


def prepare():
    assert not TRIAL.exists()
    previous=verify(PROJECT/'held_observation_v1/trial/manifest.json')
    identities=dict(previous['identities'])
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'manifest.json',dict(previous,identities=identities,
        revision='Isolated raw calibration renderer and angularly separated camera proposals'))


@contextmanager
def scope():
    with patch.object(common,'TRIAL',TRIAL),patch.object(worker,'TRIAL',TRIAL), \
         patch.object(register,'TRIAL',TRIAL),patch.object(audit,'TRIAL',TRIAL), \
         patch.object(runtime,'checkpoint',checkpoint),patch.object(audit,'checkpoint',checkpoint), \
         patch.object(views,'proposals',proposals):
        yield


if __name__=='__main__':
    actions=dict(prepare=prepare,preflight=worker.preflight,audit_preflight=audit.preflight,
        register=register.execution,execute=worker.execute,audit_physical=audit.physical)
    with scope():
        actions[sys.argv[1]]()
