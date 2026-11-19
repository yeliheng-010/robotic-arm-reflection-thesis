"""CPU独立重算控制、被动力与执行器公式；不重跑静态构型或动力学。"""
import ast
import math
import os
import subprocess
import xml.etree.ElementTree as ET
from qualified_closure_reachability_v1.common import ROOT, PROJECT, RUN, PARENT, read, save, sha, verify

TOLERANCE = 1e-10


def close(expected, actual):
    assert math.isclose(expected, actual, rel_tol=0, abs_tol=TOLERANCE), (expected, actual)


def source_checks(meta, controls):
    xml = ET.parse(RUN / 'source_snapshot/2f85.xml').getroot()
    actuator = xml.find("./actuator/general[@name='fingers_actuator']")
    for key in ('gainprm', 'biasprm', 'forcerange', 'ctrlrange'):
        expected = list(map(float, actuator.attrib[key].split()))
        assert meta['actuator'][key][:len(expected)] == expected
    spring = xml.find(".//default[@class='spring_link']/joint")
    for row in meta['joints']:
        if 'spring_link' in row['name']:
            assert row['stiffness'] == float(spring.attrib['stiffness'])
            assert row['spring_reference'] == float(spring.attrib['springref'])
    tree = ast.parse((RUN / 'source_snapshot/grasp_process.py').read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'close_gripper')
    assert [ast.literal_eval(n) for n in function.args.defaults] == [controls['default_loops'], controls['default_delta']]
    value, generated = controls['initial_command'], []
    for _ in range(controls['default_loops']):
        value = min(255., value + controls['default_delta'])
        generated.append(value)
    assert generated == controls['control_commands']
    assert controls['first_command'] == generated[0] and controls['last_command'] == generated[-1]
    assert meta['actuator']['gain_type'] == meta['actuator']['dynamics_type'] == 0
    assert meta['actuator']['bias_type'] == 1 and meta['actuator']['gear'][0] == 1
    assert meta['actuator']['ctrllimited'] and meta['actuator']['forcelimited']


def row_checks(row, entry, *, meta, controls):
    saved = entry['saved']
    assert row['envelope_index'] == entry['index'] and row['contacts'] == saved['contacts']
    assert all(joint['within_range'] for joint in row['constraints']['joints'])
    assert all(eq['active'] and eq['maximum_abs'] <= 1e-7 for eq in row['constraints']['equalities'])
    actuator = meta['actuator']
    for probe in row['force_probes']:
        close(row['angle_rad'], probe['actuator_length'])
        assert probe['actuator_velocity'] == 0 and probe['zero_velocity_counterfactual']
        control = max(actuator['ctrlrange'][0], min(actuator['ctrlrange'][1], probe['control']))
        force = actuator['gainprm'][0] * control + actuator['biasprm'][0] + actuator['biasprm'][1] * row['angle_rad']
        force = max(actuator['forcerange'][0], min(actuator['forcerange'][1], force))
        close(force, probe['actuator_force'])
        for joint, measured in zip(meta['joints'], probe['joint_forces']):
            assert joint['name'] == measured['name']
            close(joint['stiffness'] * (joint['spring_reference'] - measured['qpos']), measured['passive'])
            weight = next((w['coefficient'] for w in actuator['wraps'] if w['joint'] == joint['name']), 0.)
            close(weight * force, measured['actuator'])
    reference = row['force_probes'][1]['control']
    assert row['reference_control_within_default_command_range'] == (controls['first_command'] <= reference <= controls['last_command'])


def main():
    manifest = verify()
    result, meta, controls = [read(RUN / name) for name in ('result.json', 'parameters.json', 'controls.json')]
    source_checks(meta, controls)
    inputs = read(RUN / 'input.json')
    assert inputs['parent_closure_sha256'] == sha(PARENT / 'run/preflight/closure.json')
    assert len(result['rows']) == len(inputs['configurations']) == 5
    for row, entry in zip(result['rows'], inputs['configurations']):
        row_checks(row, entry, meta=meta, controls=controls)
    assert result['isolation']['passed'] and not result['reachability_proven'] and not result['unreachability_proven']
    assert result['new_model_calls'] == result['physical_attempts'] == result['training_runs'] == 0
    assert read(RUN / 'diagnostic_claim.json') == dict(consumed=1, input_sha256=manifest['input_sha256'])
    for path in ROOT.glob('*.py'):
        source = path.read_text(encoding='utf-8')
        assert len(source.splitlines()) <= 300
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.FunctionDef):
                assert node.end_lineno - node.lineno + 1 <= 50, (path, node.name)
    save(RUN / 'audit_result.json', dict(passed=True, independent_formula_recalculation=True,
         configurations_checked=5, force_probes_checked=15, job=os.environ['SLURM_JOB_ID'],
         model_calls=0, physics=0, training=0, result_sha256=sha(RUN / 'result.json')))
    active = 'audit-' + os.environ['SLURM_JOB_ID'] + '.log'
    identities = {str(p.relative_to(ROOT)): sha(p) for p in ROOT.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts and p.name != active}
    jobs = sorted({p.stem.rsplit('-', 1)[1] for p in ROOT.glob('*.log')})
    accounting = subprocess.run(['sacct', '-j', ','.join(jobs), '--format=JobID,State,ExitCode,Elapsed', '-n', '-P'],
                                capture_output=True, text=True, check=True).stdout
    save(RUN / 'delivery_inventory.json', dict(passed=True, identities=identities,
         frozen_identities=len(manifest['identities']), job_accounting=accounting,
         old_claim_sha256=sha(PROJECT / 'qualified_execution_v1/run/attempt_claim.json')))
    print(dict(passed=True, configurations=5, force_probes=15, files=len(identities)), flush=True)


if __name__ == '__main__':
    main()
