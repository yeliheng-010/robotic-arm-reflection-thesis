import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import op_common
import op_worker
import op_audit
from op_runtime_v2 import Session,PreviewSession

TRIAL=op_common.PARENT/'trial_gpu_v2'


def prepare():
    old=op_common.PARENT/'trial_gpu'
    op_common.verify(old/'manifest.json')
    assert op_common.read(old/'preflight/bridge.json')['planners']==[]
    assert op_common.read(old/'preflight/lifecycle.json')['released']
    assert not (old/'preflight/step.json').exists()
    op_common.prepare()


if __name__=='__main__':
    with patch.object(op_common,'TRIAL',TRIAL),patch.object(op_worker,'TRIAL',TRIAL), \
         patch.object(op_worker,'Session',Session),patch.object(op_worker,'PreviewSession',PreviewSession), \
         patch.object(op_audit,'TRIAL',TRIAL):
        {'prepare':prepare,'preflight':op_worker.preflight,'execute':op_worker.execute,'audit':op_audit.main}[sys.argv[1]]()
