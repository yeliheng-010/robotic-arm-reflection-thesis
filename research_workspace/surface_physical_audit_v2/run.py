from pathlib import Path
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from audit_motion_live import UR5e,set_robot_config,guard_context
import surface_physical_v1.audit as original
from surface_physical_v1.common import TRIAL,read,save,sha,verify,entry

ROOT=Path(__file__).resolve().parent
ORIGINAL_GEOMETRY=original.geometry


def geometry(case,trace):
    with patch.object(UR5e,'set_robot_config',set_robot_config),guard_context(case['item'],{}):
        return ORIGINAL_GEOMETRY(case,trace)


def sources():
    paths=[p for p in TRIAL.rglob('*') if p.is_file()]
    return {str(p):sha(p) for p in paths}


def main():
    diagnostic=read(ROOT/'diagnostic.json')
    assert not diagnostic['unpatched']['matches'] and diagnostic['guarded']['matches']
    before=sources()
    verify(TRIAL/'execution_manifest.json')
    case=entry()['case']
    folder=TRIAL/'cases'/str(case['item']['seed'])/'first'
    with patch.object(original,'geometry',geometry):
        result=original.complete(folder,case)
    assert sources()==before,'Original evidence changed'
    result.update(identities=before,additional_physical_attempts=0,
        original_execution_outcome=read(TRIAL/'execution_outcome.json'),
        audit_fix='Restore original robot configuration and contact guard scopes')
    save(ROOT/'audit.json',result)
    print(dict(passed=result['passed'],success=result['success'],additional_physical_attempts=0),flush=True)


if __name__=='__main__':
    main()
