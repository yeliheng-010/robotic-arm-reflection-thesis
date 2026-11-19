"""真实一次执行、暂停观测、明确释放；不自动进行第二次尝试。"""
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from sd_runtime import context as scene_context
from pair_runtime import engine_config
from loopstudy.runtime import engine_class
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from guard_scope import context as guard_context
from env_lease import retained
from live_telemetry import capture
from live_motion import context as motion_context
from live_observations import Sampler
from live_requests import build


def observe_result(result, lease, *, case, folder, recorder, bridge):
    record = result['records'][0]
    path = folder/'execution'/'result.json'
    step = dict(index=1, state=case['state'], success=bool(result['success']),
                result_path=str(path), result_sha256=sha(path))
    ledger = dict(item=case['item'], steps=[step])
    sampler = Sampler(lease.env, case['config'], item=case['item'], folder=folder/'observations',
                      attempt=1, success=step['success'])
    sampler.capture()
    if not step['success']:
        sampler.capture()
        sampler.capture()
    bundle = build(ledger, record, sampler=sampler, telemetry=recorder, bridge=bridge)
    save(folder/'model_input.json', bundle)
    save(folder/'ledger.json', ledger)
    save(folder/'observation_summary.json', dict(public=sampler.rows, private=sampler.private,
         additional_observations=max(0, len(sampler.rows)-1), remaining=sampler.budget.remaining))
    return step


def run_once(case, folder):
    folder.mkdir(parents=True, exist_ok=False)
    state, item, config = case['state'], case['item'], case['config']
    bridge, guard = {}, {}
    with scene_context(config), retained(UR5GraspEnv) as lease, capture() as recorder, \
         motion_context(item, state, recorder=recorder, trace=bridge), guard_context(item, guard):
        engine = engine_class(state)(scenario_config=engine_config(config), max_attempts=1,
                                     headless=True, task_parser='rule')
        try:
            result = engine.run(source=item['source'], destination=item['destination'], seed=item['seed'],
                                fault='none', output=folder/'execution', method='retry', context='ai-runtime-wiring')
            assert lease.env is not None and lease.close_requests >= 1 and not lease.released
            step = observe_result(result, lease, case=case, folder=folder, recorder=recorder, bridge=bridge)
        finally:
            engine.close()
            save(folder/'bridge.json', bridge)
            save(folder/'guard.json', guard)
            save(folder/'telemetry.json', dict(stride_steps=10, rows=recorder.rows))
    assert lease.released
    save(folder/'lifecycle.json', dict(retained_after_attempt=True, released=True,
                                     close_requests=lease.close_requests, actual_new_attempts=1))
    return dict(id=item['id'], success=step['success'], attempts=1,
                grasp_checked=bool(bridge.get('grasp')), carry_checked=bool(bridge.get('carry')))
