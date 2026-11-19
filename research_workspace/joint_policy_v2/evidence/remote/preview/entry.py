"""真实GPU感知后比较通用计划，在任何任务动作前强制停止。"""
import sys
from pathlib import Path
from unittest.mock import patch
import numpy as np
from reflection.__main__ import bootstrap
bootstrap()
import grasp_process as grasp
import nc_session
import jg_runtime
from qa_runtime import PlanningComplete,reject_motion
from jv_runtime import GeneralSession
from jv_register import RUN as REGRESSION
from cc_common import read,save,sha,verify

ROOT = Path(__file__).resolve().parent
RUN = ROOT/'run'


class StopSession(GeneralSession):
    def _engine(self):
        def saving(path, value):
            save(path,value)
            if path.name == 'generic_plan.json':
                expected = read(REGRESSION/'audit'/self.case['preview_name']/'plan.json')
                assert value == expected, 'Actual generic plan differs from audited snapshot'
                raise PlanningComplete()
        with patch.object(jg_runtime,'save',saving),patch.object(grasp,'_run_planners',reject_motion):
            super()._engine()


def main(name):
    manifest = verify(RUN/'manifest.json')
    entry = next(r for r in manifest['rows'] if r['name']==name)
    case = dict(entry['case'],preview_name=name)
    folder=RUN/name
    caught=False
    try:
        with patch.object(nc_session,'Session',StopSession):
            with nc_session.opened(case,case['state'],folder=folder,index=1):
                raise AssertionError('Unexpected motion entry')
    except PlanningComplete:
        caught=True
    assert caught and read(folder/'bridge.json')['planners']==[]
    assert not (folder/'step.json').exists()
    lifecycle=read(folder/'lifecycle.json')
    assert lifecycle['released'] and lifecycle['actual_close_calls']==1
    assert lifecycle['exit_exception']=='PlanningComplete'
    assert read(folder/'initial_visibility.json')['accepted']
    with np.load(Path(entry['folder'])/'span_inputs.npz') as old,np.load(folder/'span_inputs.npz') as new:
        assert set(old.files)==set(new.files)
        for field in old.files:
            np.testing.assert_array_equal(old[field],new[field])
    save(folder/'result.json',dict(passed=True,actual_plan_identical=True,inputs_identical=True,
        physical_attempts=0,model_calls=0,identities={str(p):sha(p) for p in folder.rglob('*') if p.is_file()}))
    print(dict(name=name,passed=True,physical_attempts=0),flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
