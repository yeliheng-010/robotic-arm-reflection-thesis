"""使用已审计历史现场验证输入构建，不追加模型调用或物理尝试。"""
import os
import json
from pathlib import Path
from types import SimpleNamespace
from f_common import read,save,sha
from nc_state import Branch
from live_telemetry import Recorder
from visual_requests import build

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'ai_self_route_v1'
CASE='S1_962602_varied_noisy'
FORBIDDEN=('root_cause','error_type','grasp_residual_xy','contact_details','initial_body_xyz',
           'source_center','source_half','bin_center','qualification','route_id','selected_candidate_index')


def assert_public(value):
    if isinstance(value,dict):
        assert not set(value).intersection(FORBIDDEN)
        for item in value.values():
            assert_public(item)
    elif isinstance(value,list):
        for item in value:
            assert_public(item)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    audit=read(SOURCE/'audit_962602.json')
    manifest=read(SOURCE/'manifest.json')
    assert audit['passed'] and audit['manifest_sha256']==sha(SOURCE/'manifest.json')
    case=next(c for c in manifest['cases'] if c['item']['id']==CASE)
    folder=SOURCE/'cases'/CASE/'attempt_1'
    selected=list(folder.rglob('*'))
    assert all(sha(p)==audit['identities'][str(p)] for p in selected if p.is_file())
    step=read(folder/'step.json')
    summary=read(folder/'observation_summary.json')
    recorder=Recorder()
    recorder.rows=read(folder/'telemetry.json')['rows']
    session=SimpleNamespace(folder=folder,step=step,recorder=recorder,
                            record=read(step['result_path'])['records'][0])
    view=SimpleNamespace(paths=summary['paths'],
        sampler=SimpleNamespace(rows=summary['public'],private=summary['private']))
    bundle=build(Branch(case['item'],step),session,view)
    assert_public(bundle['request'])
    assert bundle['direct_messages'][1]==bundle['diagnostic_messages'][1]
    assert len(bundle['visual']['paths'])==2
    assert all(sha(p)==h for p,h in zip(bundle['visual']['paths'],bundle['visual']['sha256']))
    assert bundle['request']['after_attempt']==1 and bundle['request']['budget']['executions_remaining']==2
    assert str(folder/'contacts.jsonl') not in json.dumps(bundle['request'])
    save(ROOT/'input.json',bundle)
    save(ROOT/'verification.json',dict(passed=True,source=CASE,source_attempt=1,
        checks=['audited_source','input_boundary','mode_fairness','two_image_identity','budget'],
        physical_attempts=0,model_calls=0,training_ready=False,
        identities={str(p):sha(p) for p in [Path(__file__),ROOT/'visual_requests.py',ROOT/'input.json']}))
    print(dict(passed=True,checks=5,physical_attempts=0,model_calls=0),flush=True)


if __name__=='__main__':
    main()
