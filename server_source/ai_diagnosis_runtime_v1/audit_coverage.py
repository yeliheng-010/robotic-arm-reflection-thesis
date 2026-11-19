"""最终覆盖门禁覆盖早期过宽布尔值；不更改已冻结审计与物理证据。"""
import os
from pathlib import Path
from unittest.mock import patch
import unittest
from reflection.__main__ import bootstrap
bootstrap()
from sd_common import read, save, sha
from live_run import verify
import audit_sensor_live
import audit_live
from coverage_gate import evaluate

ROOT = Path(__file__).resolve().parent
FILES = ('coverage_gate.py', 'test_coverage.py', 'audit_coverage.py', 'coverage.sbatch')


def sensor_rejection(folder, config, *, name):
    def changed(path):
        value = read(path)
        if name == 'surface' and path.name == 'public.json':
            value['observed']['source']['surface_centroid_world_m'][0] += .1
        if name == 'noise' and path.name == 'audit.json':
            value['stats']['noise_rmse_m'] += .1
        return value
    with patch.object(audit_sensor_live, 'read', changed):
        try:
            audit_sensor_live.frame(folder, config, index=0)
        except AssertionError:
            return dict(kind=name, rejected=True, source_modified=False)
    raise AssertionError('Sensor mutation was accepted: '+name)


def telemetry_rejection(folder):
    ledger, bridge = read(folder/'ledger.json'), read(folder/'bridge.json')
    record = read(ledger['steps'][0]['result_path'])['records'][0]
    def changed(path):
        value = read(path)
        if path.name == 'telemetry.json':
            value['rows'][0]['step'] += 1
        return value
    with patch.object(audit_live, 'read', changed):
        try:
            audit_live.public_input(folder, ledger, record=record, bridge=bridge)
        except AssertionError:
            return dict(kind='telemetry_stride', rejected=True, source_modified=False)
    raise AssertionError('Telemetry mutation was accepted')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest, audit = verify(), read(ROOT/'verification.json')
    assert not (ROOT/'coverage_verification.json').exists()
    suite = unittest.TestSuite([unittest.TestLoader().discover(str(ROOT)),
        unittest.TestLoader().discover(str(ROOT.parent/'ai_diagnosis_v1'))])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    assert result.wasSuccessful() and audit['passed']
    assert all(sha(p) == h for p, h in audit['identities'].items())
    case = manifest['cases'][1]
    folder = ROOT/'runs'/case['item']['id']
    rejected = [sensor_rejection(folder/'observations/observation_0', case['config'], name=name)
                for name in ('surface', 'noise')]
    rejected.append(telemetry_rejection(folder))
    gate = evaluate(audit['rows'])
    value = dict(passed=True, tests=result.testsRun, coverage=gate, tamper_checks=rejected,
        authoritative_model_smoke_gate=gate['model_smoke_gate'],
        supersedes='verification.json:model_smoke_gate (motion-only check omitted failed-branch coverage)',
        model_calls=0, training_runs=0, actual_new_attempts=sum(r['attempts'] for r in audit['rows']),
        execution_sha256=sha(ROOT/'manifest.json'), revision_sha256=sha(ROOT/'revision_manifest.json'),
        audit_sha256=sha(ROOT/'verification.json'),
        identities={str(ROOT/n): sha(ROOT/n) for n in FILES})
    assert all(sha(p) == h for p, h in audit['identities'].items())
    save(ROOT/'coverage_verification.json', value)
    print(value, flush=True)


if __name__ == '__main__':
    main()
