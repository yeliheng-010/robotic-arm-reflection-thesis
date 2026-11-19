"""独立接线审计；失败门禁不调用模型，不追加物理执行。"""
import json
import os
from pathlib import Path
from types import SimpleNamespace
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from pair_run import audit_sensor
from live_run import verify
from live_requests_v2 import build
from sensor_math import uniform_rows
from audit_sensor_live import audit as sensor_audit
from audit_motion_live import audit as motion_audit

ROOT = Path(__file__).resolve().parent
FORBIDDEN = {'error_type', 'diagnosis', 'candidate_trace', 'initial_body_xyz', 'clean',
             'seed', 'seed_components', 'private', 'truth', 'noise_rmse_m', 'quality'}
TELEMETRY = {'step', 'time_s', 'action', 'q_rad', 'tcp_fk_xyz_m', 'command_tcp_xyz_m',
             'gripper_joint_rad', 'source'}


def private_keys(value):
    if isinstance(value, dict):
        assert not FORBIDDEN.intersection(value), FORBIDDEN.intersection(value)
        for child in value.values():
            private_keys(child)
    elif isinstance(value, list):
        for child in value:
            private_keys(child)


def public_input(folder, ledger, *, record, bridge):
    telemetry = read(folder/'telemetry.json')
    rows = telemetry['rows']
    assert telemetry['stride_steps'] == 10
    assert [r['step'] for r in rows] == list(range(10, (len(rows)+1)*10, 10))
    assert all(set(r) == TELEMETRY for r in rows)
    assert all(a['time_s'] < b['time_s'] for a, b in zip(rows, rows[1:]))
    summary = read(folder/'observation_summary.json')
    sampler = SimpleNamespace(rows=summary['public'], budget=SimpleNamespace(remaining=summary['remaining']))
    recorder = SimpleNamespace(public=lambda: dict(sampling='fixed_every_10_physics_steps',
        summary='uniform_time_index_subset', samples=uniform_rows(rows), total_samples=len(rows)))
    expected = build(ledger, record, sampler=sampler, telemetry=recorder, bridge=bridge)
    actual = read(folder/'model_input.json')
    assert expected == actual
    assert actual['direct_messages'][1] == actual['diagnostic_messages'][1]
    private_keys(actual['request'])
    assert 'SELECT_GRASP' not in [r['id'] for r in actual['request']['actions']]
    return dict(passed=True, telemetry_samples=len(rows), shared_user_input=True,
                actions=[r['id'] for r in actual['request']['actions']])


def inspect_case(case):
    folder = ROOT/'runs'/case['item']['id']
    ledger = read(folder/'ledger.json')
    lifecycle = lifecycle_evidence(folder)
    assert len(ledger['steps']) == 1 and ledger['item'] == case['item']
    step = ledger['steps'][0]
    assert step['index'] == 1 and step['state'] == case['state']
    assert sha(step['result_path']) == step['result_sha256']
    result = read(step['result_path'])
    assert len(result['records']) == 1 and result['success'] == step['success']
    record = result['records'][0]
    assert record['parameters'] == step['state']['parameters']
    guard, bridge = read(folder/'guard.json'), read(folder/'bridge.json')
    assert guard['strict_contacts']
    if step['success']:
        assert guard['release_checked'] and guard['open_called'] and guard['reason'] is None
    return dict(id=case['item']['id'], success=step['success'], attempts=1,
                error=(record['error'] or {}).get('error_type'),
                execution_sensor=audit_sensor(record['domain_randomization']['sensor_frames'], case['config'], index=1),
                observation=sensor_audit(folder, case, success=step['success']),
                motion=motion_audit(case, bridge),
                model_input=public_input(folder, ledger, record=record, bridge=bridge), lifecycle=lifecycle)


def lifecycle_evidence(folder):
    if (folder/'lifecycle.json').exists():
        row = read(folder/'lifecycle.json')
        assert row['released'] and row['retained_after_attempt']
        assert row['actual_new_attempts'] == 1 and row['close_requests'] >= 1
        return dict(row, evidence='runtime_event')
    recovery = read(folder/'recovery.json')
    assert recovery['source_job'] == 5880 and recovery['physical_rerun'] is False
    assert recovery['log_sha256'] == sha(ROOT/'run-5880.log')
    text = (ROOT/'run-5880.log').read_text()
    assert 'ValueError: Bad command vector' in text
    assert 'lease.release' not in text and 'lease.env is not None' not in text
    return dict(evidence='exception_cleanup_and_process_exit', runtime_close_event_missing=True,
                limitation='Successful close inferred from unwinding; not a saved runtime flag')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest, complete = verify(), read(ROOT/'run_complete.json')
    revision = read(ROOT/'revision_manifest.json')
    assert all(sha(p) == h for p, h in revision['identities'].items())
    assert complete['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert complete['actual_new_attempts'] <= 2 and complete['model_calls'] == 0
    rows = [inspect_case(c) for c in manifest['cases']]
    assert sum(r['attempts'] for r in rows) == complete['actual_new_attempts']
    gate = (all(r['motion']['actual_motion'] and r['motion']['grasp_checked'] for r in rows)
            and rows[1]['lifecycle']['evidence'] == 'runtime_event')
    verify()
    artifacts = [p for p in (ROOT/'runs').rglob('*') if p.is_file()]
    value = dict(passed=True, model_smoke_gate=gate, rows=rows,
                 manifest_sha256=sha(ROOT/'manifest.json'), model_calls=0, training_runs=0,
                 identities={str(p): sha(p) for p in artifacts})
    save(ROOT/'verification.json', value)
    print(json.dumps({k: v for k, v in value.items() if k != 'identities'}), flush=True)


if __name__ == '__main__':
    main()
