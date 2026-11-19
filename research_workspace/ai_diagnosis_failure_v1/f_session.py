"""只运行一条工程中止分支，不替代或改写旧物理验收。"""
from reflection.__main__ import bootstrap
bootstrap()
from sd_runtime import context as scene_context
from pair_runtime import engine_config
from loopstudy.runtime import engine_class
from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
from live_telemetry import capture
from live_motion import context as motion_context
from guard_scope import context as guard_context
from f_common import save, sha
from f_lifetime import managed
from f_stop import EngineeringStop, PostObservationProbe, context as stop_context
from f_observe import observe


def execute(case, engine, *, folder, fixture):
    item = case['item']
    try:
        result = engine.run(source=item['source'], destination=item['destination'], seed=item['seed'],
                            fault='none', output=folder/'execution', method='retry', context='engineering-lifecycle')
    except EngineeringStop:
        assert fixture['triggered']
        record = dict(parameters=case['state']['parameters'], diagnostics={'action': 'move_to_point'},
                      physical_success=None, accepted=False, status='engineering_interrupted')
        result = dict(success=False, records=[record], outcome_class='engineered_abort',
                      physical_success_evaluated=False, natural_failure=False)
        save(folder/'engineering_result.json', result)
        return result
    save(folder/'unexpected_result.json', result)
    raise RuntimeError('Registered checkpoint not reached; preserve earlier outcome and stop')


def retained_work(case, lease, *, folder, recorder, bridge, guard, fixture):
    engine = engine_class(case['state'])(scenario_config=engine_config(case['config']), max_attempts=1,
                                        headless=True, task_parser='rule')
    try:
        result = execute(case, engine, folder=folder, fixture=fixture)
        lease.mark_retained()
        path = folder/'engineering_result.json'
        step = dict(index=1, state=case['state'], success=False, result_path=str(path), result_sha256=sha(path))
        ledger = dict(item=case['item'], steps=[step], outcome_class='engineered_abort')
        save(folder/'ledger.json', ledger)
        observe(lease, case, folder=folder, ledger=ledger, record=result['records'][0],
                recorder=recorder, bridge=bridge)
        save(folder/'post_observation_probe.json', dict(armed=True, after_saved_frames=3))
        raise PostObservationProbe('Pre-registered cleanup probe after saved observations')
    finally:
        engine.close()
        save(folder/'bridge.json', bridge)
        save(folder/'guard.json', guard)
        save(folder/'fixture.json', fixture)
        save(folder/'telemetry.json', dict(stride_steps=10, rows=recorder.rows))


def run_once(case, folder):
    folder.mkdir(parents=True, exist_ok=False)
    bridge, guard, fixture = {}, {}, {}
    save(folder/'attempt_started.json', dict(actual_new_attempts=1, condition=case['item']['id']))
    try:
        with scene_context(case['config']), managed(UR5GraspEnv, folder) as lease, capture() as recorder, \
             motion_context(case['item'], case['state'], recorder=recorder, trace=bridge), \
             guard_context(case['item'], guard), stop_context(fixture):
            retained_work(case, lease, folder=folder, recorder=recorder, bridge=bridge, guard=guard, fixture=fixture)
    except PostObservationProbe:
        assert lease.state['released'] and lease.state['close_error'] is None
    else:
        raise AssertionError('Cleanup probe was not exercised')
    return dict(id=case['item']['id'], attempts=1, outcome_class='engineered_abort',
                natural_failures=0, model_calls=0, training_runs=0, exception_cleanup_verified=True)
