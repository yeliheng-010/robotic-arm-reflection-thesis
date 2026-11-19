"""本地归档与解析公式复核，不加载MuJoCo或运行控制器。"""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
EVIDENCE, REMOTE = ROOT / 'evidence', ROOT / 'evidence/remote'
RUN = REMOTE / 'run'
OUTPUT = EVIDENCE / 'FINAL_VERIFICATION.json'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files():
    rows = read(EVIDENCE / 'DELIVERY.json')['files']
    seen, sources = set(), 0
    for row in rows:
        path = (REMOTE / row['path']).resolve()
        assert path.is_relative_to(REMOTE.resolve())
        assert row['path'] not in seen and row['sha256'] == sha(path)
        seen.add(row['path'])
        if len(Path(row['path']).parts) == 1 and path.suffix in ('.py', '.sbatch', '.md'):
            assert row['sha256'] == sha(ROOT / row['path'])
            sources += 1
    inventory = read(RUN / 'delivery_inventory.json')
    for name, expected in inventory['identities'].items():
        assert sha(REMOTE / name) == expected
    old = ROOT.parent / 'qualified_execution_v1/evidence/remote/run/attempt_claim.json'
    assert read(old)['consumed'] == 1 and sha(old) == inventory['old_claim_sha256']
    return dict(downloaded=len(rows), local_remote_sources=sources,
                frozen_identities=inventory['frozen_identities'], old_claim_unchanged=True)


def formula_checks():
    result, meta, controls = [read(RUN / name) for name in ('result.json', 'parameters.json', 'controls.json')]
    old = ROOT.parent / 'qualified_checkpoint_preflight_v1/evidence/remote/run/preflight/closure.json'
    parent = read(old)
    inputs = read(RUN / 'input.json')
    assert inputs['parent_closure_sha256'] == sha(old)
    assert [r['saved'] for r in inputs['configurations']] == [r for r in parent['envelope'] if r['valid'] and r['contacts']]
    actuator = meta['actuator']
    probes, rows = 0, []
    for actual, entry in zip(result['rows'], inputs['configurations']):
        assert actual['contacts'] == entry['saved']['contacts']
        assert all(row['within_range'] for row in actual['constraints']['joints'])
        assert all(row['active'] and row['maximum_abs'] <= 1e-7 for row in actual['constraints']['equalities'])
        for probe in actual['force_probes']:
            force = actuator['gainprm'][0] * probe['control'] + actuator['biasprm'][0] + actuator['biasprm'][1] * probe['actuator_length']
            expected = max(actuator['forcerange'][0], min(actuator['forcerange'][1], force))
            assert math.isclose(expected, probe['actuator_force'], abs_tol=1e-10, rel_tol=0)
            for parameter, joint in zip(meta['joints'], probe['joint_forces']):
                expected = parameter['stiffness'] * (parameter['spring_reference'] - joint['qpos'])
                assert math.isclose(expected, joint['passive'], abs_tol=1e-10, rel_tol=0)
            probes += 1
        rows.append(dict(driver=actual['angle_rad'], spring=actual['spring_rad'],
                         zero_actuator_force_reference_control=actual['force_probes'][1]['control'],
                         last_command_actuator_force=actual['force_probes'][2]['actuator_force']))
    assert len(rows) == 5 and probes == 15
    assert result['isolation']['passed'] and result['guard']['blocked_task_integration_requests'] == 0
    assert result['new_model_calls'] == result['physical_attempts'] == result['training_runs'] == 0
    assert not result['reachability_proven'] and not result['unreachability_proven'] and not result['safety_gate_changed']
    return dict(configurations=5, force_probes=15, controller_first=controls['first_command'],
                controller_last=controls['last_command'], rows=rows, guard=result['guard'],
                nominal_zero_speed_target=actuator['gainprm'][0] * controls['last_command'] / -actuator['biasprm'][1],
                isolation=result['isolation'], dynamic_reachability='unresolved', gate_changed=False)


def sampling_gap():
    path = ROOT.parent / 'qualified_checkpoint_preflight_v1/evidence/remote/run/preflight/closure.json'
    closure = read(path)
    values = []
    for row in read(RUN / 'result.json')['rows']:
        valid = [r for r in closure['envelope'] if r['valid'] and
                 math.isclose(r['angle_rad'], row['angle_rad'], abs_tol=1e-12)]
        assert all(r['linkage']['left']['joints'][1] == r['linkage']['right']['joints'][1] == r['spring_rad'] for r in valid)
        values.append(dict(driver_angle=row['angle_rad'], distinct_valid_symmetric_springs=len(valid)))
    equalities = read(RUN / 'parameters.json')['equalities']
    joint_pairs = [row['names'] for row in equalities if row['type'] == 2]
    assert joint_pairs == [['right_driver_joint', 'left_driver_joint']]
    return dict(parent_sha256=sha(path), symmetric_sampling=True, equality_joint_pairs=joint_pairs,
                per_driver=values, asymmetric_dynamics_tested=False)


def main():
    value = dict(checked_at_utc=datetime.now(timezone.utc).isoformat(), passed=True,
                 files=files(), diagnosis=formula_checks(), sampling=sampling_gap(), verifier_sha256=sha(Path(__file__)))
    audit = read(RUN / 'audit_result.json')
    assert audit['passed'] and audit['result_sha256'] == sha(RUN / 'result.json')
    manifest = read(RUN / 'manifest.json')
    assert read(RUN / 'diagnostic_claim.json') == dict(consumed=1, input_sha256=manifest['input_sha256'])
    assert sha(RUN / 'input.json') == manifest['input_sha256']
    links = re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', (ROOT / 'REPORT.md').read_text(encoding='utf-8'))
    assert all((ROOT / link).is_file() or (ROOT / link).resolve() == OUTPUT for link in links)
    value.update(report_links_checked=len(links), pending_diagnostic_scope=[], physical=0, model_calls=0, training=0)
    if '--write' in sys.argv:
        with OUTPUT.open('x', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    assert OUTPUT.is_file() and all((ROOT / link).is_file() for link in links)
    print(json.dumps(value, ensure_ascii=True))


if __name__ == '__main__':
    main()
