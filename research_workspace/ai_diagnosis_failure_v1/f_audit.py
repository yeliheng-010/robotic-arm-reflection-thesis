"""独立重算三帧和几何；工程中止仅验证接口，不能充作自然故障。"""
import os
from types import SimpleNamespace
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
from f_common import ROOT, read, save, sha, verify
from f_requests import build
from sensor_math import uniform_rows
from audit_sensor_live import audit as audit_sensor
from audit_motion_live import audit as audit_motion
from coverage_gate import evaluate
import audit_live


def snapshot(folder, ledger, *, record, bridge):
    rows = read(folder/'telemetry.json')['rows']
    recorder = SimpleNamespace(public=lambda: dict(sampling='fixed_every_10_physics_steps',
        summary='uniform_time_index_subset', samples=uniform_rows(rows), total_samples=len(rows)))
    for index in range(3):
        summary = read(folder/f'observation_summary_{index}.json')
        assert len(summary['public']) == index+1 and summary['remaining'] == 2-index
        assert [r['observation_index'] for r in summary['public']] == list(range(index+1))
        sampler = SimpleNamespace(rows=summary['public'], budget=SimpleNamespace(remaining=2-index))
        expected = build(ledger, record, sampler=sampler, telemetry=recorder, bridge=bridge)
        value = read(folder/f'model_input_{index}.json')
        assert expected == value and value['direct_messages'][1] == value['diagnostic_messages'][1]
        audit_live.private_keys(value['request'])
        assert 'engineering' not in str(value).lower() and 'PostObservationProbe' not in str(value)
    return dict(passed=True, replay_snapshot=0, future_frames_excluded=True,
                initial_sha256=sha(folder/'model_input_0.json'))


def lifecycle(folder):
    value = read(folder/'lifecycle.json')
    assert value['released'] and value['retained_after_attempt'] and value['close_error'] is None
    assert value['close_requests'] == value['actual_close_calls'] == 1
    assert value['exit_exception'] == 'PostObservationProbe'
    assert value['events'] == ['close_deferred', 'retained_for_observation', 'exception_unwind',
                                'close_started', 'close_completed']
    assert read(folder/'post_observation_probe.json') == dict(armed=True, after_saved_frames=3)
    return dict(value, evidence='runtime_event')


def inspect(case):
    folder = ROOT/'run'
    ledger, result = read(folder/'ledger.json'), read(folder/'engineering_result.json')
    assert len(ledger['steps']) == 1 and ledger['steps'][0]['state'] == case['state']
    assert sha(folder/'engineering_result.json') == ledger['steps'][0]['result_sha256']
    assert result['outcome_class'] == 'engineered_abort' and result['natural_failure'] is False
    assert result['success'] is False and result['physical_success_evaluated'] is False
    fixture, guard, bridge = (read(folder/(name+'.json')) for name in ('fixture', 'guard', 'bridge'))
    assert fixture['triggered'] and fixture['checkpoint'] == 'after_move_to_point_before_release'
    assert guard['strict_contacts'] and not guard['open_called'] and not guard['release_checked']
    budget = read(folder/'observation_budget_check.json')
    assert budget == dict(rejected=True, state_unchanged=True, count=3, remaining=0, render_not_started=True)
    record = result['records'][0]
    with patch.object(audit_live, 'build', build):
        public = audit_live.public_input(folder, ledger, record=record, bridge=bridge)
    prefix = snapshot(folder, ledger, record=record, bridge=bridge)
    return dict(id=case['item']['id'], success=False, outcome_class='engineered_abort',
                observation=audit_sensor(folder, case, success=False), motion=audit_motion(case, bridge),
                lifecycle=lifecycle(folder), model_input=public, snapshot=prefix, fourth_observation_rejected=True)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest, complete = verify(), read(ROOT/'run_complete.json')
    assert complete['manifest_sha256'] == sha(ROOT/'manifest.json') and complete['attempts'] == 1
    row = inspect(manifest['case'])
    coverage = evaluate([row])
    assert coverage['model_smoke_gate']
    verify()
    artifacts = [p for p in (ROOT/'run').rglob('*') if p.is_file()]
    value = dict(passed=True, model_smoke_gate=True, row=row, coverage=coverage,
                 actual_new_attempts=1, natural_failure_samples=0, model_calls=0, training_runs=0,
                 manifest_sha256=sha(ROOT/'manifest.json'), identities={str(p): sha(p) for p in artifacts})
    save(ROOT/'verification.json', value)
    print({k: v for k, v in value.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()
