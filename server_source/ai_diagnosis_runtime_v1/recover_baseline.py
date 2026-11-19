"""只恢复已保存的成功结果与单帧，不创建环境、不重跑物理执行。"""
from types import SimpleNamespace
from sd_common import read, save, sha
from sensor_math import uniform_rows
from live_requests_v2 import build


def recover(case, root):
    folder = root/'runs'/case['item']['id']
    result_path = folder/'execution/result.json'
    result = read(result_path)
    assert result['success'] and len(result['records']) == 1
    assert not (folder/'ledger.json').exists()
    public = read(folder/'observations/observation_0/public.json')
    private = read(folder/'observations/observation_0/audit.json')
    assert len(list((folder/'observations').glob('observation_*'))) == 1
    step = dict(index=1, state=case['state'], success=True, result_path=str(result_path),
                result_sha256=sha(result_path))
    ledger = dict(item=case['item'], steps=[step])
    rows = read(folder/'telemetry.json')['rows']
    recorder = SimpleNamespace(public=lambda: dict(sampling='fixed_every_10_physics_steps',
        summary='uniform_time_index_subset', samples=uniform_rows(rows), total_samples=len(rows)))
    sampler = SimpleNamespace(rows=[public], budget=SimpleNamespace(remaining=2))
    request = build(ledger, result['records'][0], sampler=sampler, telemetry=recorder,
                    bridge=read(folder/'bridge.json'))
    save(folder/'model_input.json', request)
    save(folder/'ledger.json', ledger)
    save(folder/'observation_summary.json', dict(public=[public], private=[private],
         additional_observations=0, remaining=2))
    save(folder/'recovery.json', dict(physical_rerun=False, observed_frames_reused=1,
         source_job=5880, cause='in_memory_tuple_rejected_by_json_list_contract',
         lifecycle_event_missing=True, cleanup_evidence='exception_unwound_retained_context_no_close_error',
         log_sha256=sha(root/'run-5880.log'), result_sha256=sha(result_path)))
    return dict(id=case['item']['id'], success=True, attempts=1, reused_physical_result=True)
