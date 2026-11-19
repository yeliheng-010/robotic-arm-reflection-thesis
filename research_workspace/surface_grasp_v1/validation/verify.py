"""本地核对下载证据及冻结输入重建；不运行物理仿真。"""
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
from model_grasp_gpu_v1.observed import prepare
from surface_grasp_v1.common import read,sha,save

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
REMOTE=ROOT/'evidence/remote'
REMOTE_ROOT='/home/yeliheng/grasp_server/'
NOMINAL=[0.8627476591359693,0.47132895753821524,0.7858284072438437]


def sources():
    manifest=read(REMOTE/'manifest.json')
    entries=read(ROOT/'LOCAL_DELIVERY.json')['entries']
    for row in entries:
        assert sha(REMOTE/row['path'])==row['sha256'],row['path']
    verified=[]
    for name,digest in manifest['identities'].items():
        prefix=REMOTE_ROOT+'surface_grasp_v1/'
        if name.startswith(prefix):
            path=Path(name.removeprefix(prefix))
            assert sha(REMOTE/path)==digest,path
            if path.suffix in ('.py','.md','.sbatch'):
                assert sha(ROOT/path)==digest,path
                verified.append(str(path))
    return dict(files=len(entries),source_files=len(verified))


def reconstructed():
    local=read(ROOT/'LOCAL_GENERATION.json')
    remote=read(REMOTE/'generation.json')
    assert local['summary']==remote['summary']
    assert len(local['catalogue'])==len(remote['catalogue'])==512
    maximum=0.
    for a,b in zip(local['catalogue'],remote['catalogue']):
        for key in ('id','anchor_id','family','roll_deg','insertion_m'):
            assert a[key]==b[key],(a['id'],key)
        delta=float(np.max(np.abs(np.array(a['proposal']['pose'])-b['proposal']['pose'])))
        maximum=max(maximum,delta)
        assert delta<1e-12,a['id']
        assert abs(a['observed_distance_proxy_m']-b['observed_distance_proxy_m'])<1e-12
        assert abs(a['proposal']['required_width_m']-b['proposal']['required_width_m'])<1e-12
    source=PROJECT/'model_grasp_gpu_v1/evidence/source_964347'
    with np.load(source/'span_inputs.npz') as arrays:
        observation=prepare(arrays,read(source/'span_guard.json'),NOMINAL)
    data=json.dumps(observation,ensure_ascii=False,indent=2,allow_nan=False).encode()
    expected=read(PROJECT/'model_grasp_gpu_v1/evidence/remote/preflight.json')
    assert hashlib.sha256(data).hexdigest()==expected['observation_sha256']
    assert sha(source/'span_inputs.npz')==expected['source_sha256']
    return dict(local_reconstruction=True,max_pose_delta=maximum,original_observation_hash_matched=True)


def endpoints():
    a,b=read(REMOTE/'probe/result.json'),read(REMOTE/'audit/result.json')
    rows=read(REMOTE/'probe/endpoints.json')
    assert rows==read(REMOTE/'audit/endpoints.json')
    assert len(rows)==4096==a['endpoint_checks']==b['endpoint_checks']
    assert sum(row['ok'] for row in rows)==200==a['safe_endpoints']==b['safe_endpoints']
    assert len({r['action_id'] for r in rows if r['ok']})==138
    for result in (a,b):
        assert result['passed'] and result['complete'] and result['integration_identical']
        assert not result['budget_exhausted'] and result['physical_attempts']==result['model_calls']==0
        assert result['endpoints_sha256']==sha(REMOTE/'probe/endpoints.json')
    assert b['independent']
    return dict(endpoint_checks=4096,safe_endpoints=200,safe_actions=138,
                reasons=dict(Counter(row.get('reason') or 'ok' for row in rows)),independent_endpoints_identical=True)


def paths():
    a,b=read(REMOTE/'paths/probe/result.json'),read(REMOTE/'paths/audit/result.json')
    assert a['ready'] and b['ready'] and b['independent']
    assert a['checked']==b['checked'] and len(a['checked'])==1
    name=a['checked'][0]['candidate']
    for filename in ('private_plan.json','private_trace.json','private_events.json','state_check.json'):
        assert read(REMOTE/'paths/probe'/name/filename)==read(REMOTE/'paths/audit'/name/filename)
    state=read(REMOTE/'paths/audit'/name/'state_check.json')
    assert state['integration_identical'] and state['unchanged'] and state['physical_attempts']==0
    plan=read(REMOTE/'paths/audit'/name/'private_plan.json')
    assert plan['selected']['feasible'] and plan['selected']['lift']==.2
    return dict(path_candidates_checked=1,static_path_ready=True,independent_path_identical=True,
                candidate=name,static_limitations=plan['limitations'])


def structure():
    files=list(ROOT.glob('*.py'))+[Path(__file__)]
    for path in files:
        text=path.read_text(encoding='utf-8')
        assert len(text.splitlines())<=300,path
        tree=ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node,ast.FunctionDef):
                assert node.end_lineno-node.lineno+1<=50,(path,node.name)
                assert len(node.args.posonlyargs)+len(node.args.args)<=3,(path,node.name)
    return dict(python_files_checked=len(files),syntax_and_size_passed=True)


def main():
    result=dict(passed=True,**sources(),**reconstructed(),**endpoints(),**paths(),**structure(),
                physical_attempts=0,model_calls=0,training_runs=0,task_success=None,training_eligible=False)
    scheduler=[line.split() for line in (REMOTE/'scheduler_final.txt').read_text().splitlines() if line.strip()]
    assert {row[0] for row in scheduler}=={'6484','6484.batch'}
    assert all(row[1:3]==['COMPLETED','0:0'] for row in scheduler)
    save(ROOT/'FINAL_VERIFICATION.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
