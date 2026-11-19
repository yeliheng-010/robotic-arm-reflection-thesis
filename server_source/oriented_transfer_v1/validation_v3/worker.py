"""修订版本正式入口：独立目录、显式预算、完整结果优先原独立审计。"""
import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import op_common
import op_worker
import op_audit
from oc_runtime import Session, PreviewSession
from cc_common import read, save, sha, verify
from register import ROOT, TRIAL, prepare, execution
from gate import claim


def execute():
    claim(TRIAL)
    outcome = dict(returned=False, exception=None, model_calls=0, training_updates=0)
    try:
        op_worker.execute()
        outcome['returned'] = True
    except BaseException as error:
        outcome.update(exception=type(error).__name__, message=str(error))
        raise
    finally:
        save(TRIAL/'execution_outcome.json', outcome)


def audit():
    verify(TRIAL/'execution_manifest.json')
    op_audit.main()
    folder = TRIAL/'cases/964345/first'
    lifecycle = read(folder/'lifecycle.json')
    assert lifecycle['released'] and lifecycle['actual_close_calls'] == 1
    assert lifecycle['close_error'] is None
    result = read(TRIAL/'audit.json')
    assert result['passed']
    save(TRIAL/'completion.json', dict(audited=True, task_success=result['success'],
        physical_attempts=1, independent_new_conditions=0,
        audit_sha256=sha(TRIAL/'audit.json'), lifecycle=lifecycle,
        execution_outcome=read(TRIAL/'execution_outcome.json')))


def main(action):
    with patch.object(op_common, 'TRIAL', TRIAL), patch.object(op_worker, 'TRIAL', TRIAL), \
         patch.object(op_worker, 'Session', Session), patch.object(op_worker, 'PreviewSession', PreviewSession), \
         patch.object(op_audit, 'TRIAL', TRIAL):
        {'prepare': prepare, 'preflight': op_worker.preflight, 'register': execution,
            'execute': execute, 'audit': audit}[action]()


if __name__ == '__main__':
    main(sys.argv[1])
