"""只校验方案与旧证据，不生成候选、不重算几何或推进仿真。"""
import inspect
from pathlib import Path
from qualified_scene_static_audit_v2.audit import verify as verify_parent
from qualified_scene_candidate_v1.common import PROJECT, read, sha, require
from qualified_closure_dynamics_v1.protocol import commands

ROOT = Path(__file__).resolve().parent
EXPECTED_BUDGET = dict(trajectories=1, setup_steps=0, task_steps=1000, model_calls=0,
    full_task_attempts=0, training_runs=0, zero_integration_audits=1,
    job_wall_seconds=600, loop_wall_seconds=120)


def sources():
    identities, records = verify_parent()
    for name, digest in read(ROOT / 'BINDINGS.json').items():
        require(sha(PROJECT / name) == digest, 'Changed plan source: '+name)
        identities[str(PROJECT / name)] = digest
    return identities, records


def protocol_check(plan):
    require(plan['diagnostic_id'] == 'qualified_closure_mjb_v1-978505', 'Wrong new diagnostic ID')
    require(plan['status'] == 'proposed_not_authorized', 'Unexpected proposal status')
    for flag in ('execution_authorized', 'entrypoint_ready', 'production_ready',
                 'dynamics_validated', 'execution_registration_created'):
        require(plan[flag] is False, 'Plan cannot grant '+flag)
    budget = plan['proposed_budget']
    require(budget == EXPECTED_BUDGET and all(type(x) is int for x in budget.values()), 'Wrong budget')
    require(plan['candidate']['transform_again'] is plan['candidate']['clear_state_again'] is False,
            'Candidate must be restored unchanged')
    require(plan['identity_policy'] == 'all_626_reloaded_fields_exact', 'Identity relaxation')
    require(plan['initial_tolerances'] == dict(connect_m=1e-7, driver_rad=1e-7, attach_residual=1e-6),
            'Initial tolerances changed')
    require(plan['stop']['check_every_step'] and plan['stop']['stop_on_either'], 'Missing stop checks')
    require(plan['stop']['timings'] == ['raw_post_step_cache', 'independent_forward'], 'Wrong timings')
    require(plan['stop']['extra_dwell_steps'] == plan['stop']['retries'] == 0, 'Unexpected extra steps')
    for name in ('authorization.json', 'execute.sbatch', 'run'):
        require(not (ROOT / name).exists(), 'Unexpected execution artifact: '+name)
    require(not (PROJECT / 'qualified_closure_mjb_v1').exists(), 'Implementation scope changed')


def evidence_check(plan):
    model = plan['model']
    path = PROJECT / model['path']
    require(path.stat().st_size == model['size'] and sha(path) == model['sha256'], 'Wrong binary')
    require(sha(PROJECT / plan['candidate']['path']) == plan['candidate']['sha256'], 'Wrong candidate')
    metadata, baseline = read(PROJECT / model['metadata']), read(PROJECT / model['reloaded_fields'])
    audit = read(PROJECT / model['static_audit'])
    require(audit['passed'] and audit['static_geometry_passed'] and audit['state_unchanged'], 'Static audit failed')
    require(audit['model_sha256'] == model['sha256'] == metadata['model_sha256'], 'Model binding differs')
    require(metadata['candidate_sha256'] == plan['candidate']['sha256'], 'Candidate binding differs')
    require(audit['integration_state_size'] == plan['candidate']['state_size'] == 1086, 'State size differs')
    require(len(baseline) == model['field_count'] == 626 and baseline['signature'] == '0', 'Wrong baseline')
    differing = sorted(k for k in set(baseline) | set(metadata['model_fields'])
                       if baseline.get(k) != metadata['model_fields'].get(k))
    require(differing == ['signature'], 'Unexpected compiled/reloaded difference')
    for name in ('timestep', 'integrator', 'solver'):
        key = 'timestep_seconds' if name == 'timestep' else name
        require(baseline['opt.'+name] == repr(model[key]), 'Compiled option differs: '+name)
    require(metadata['mujoco_version'] == model['mujoco_version'] == '3.3.7', 'Version differs')
    return dict(model_sha256=model['sha256'], model_size=model['size'], baseline_fields=len(baseline),
                candidate_sha256=plan['candidate']['sha256'], static_audit_job=audit['job'])


def control_check(plan):
    controls = read(PROJECT / plan['control']['saved_commands'])
    inputs = read(PROJECT / plan['control']['inputs'])
    require(plan['arm_command'] == inputs['command'] and len(inputs['command']) == 6, 'Wrong arm command')
    values = commands()
    require(values == controls['control_commands'] and len(values) == plan['control']['commands'] == 1000,
            'Controls differ')
    require(plan['control']['initial'] == controls['initial_command'] == 0.0, 'Wrong initial control')
    require(plan['control']['delta'] == controls['default_delta'] == 0.2, 'Wrong control increment')
    require(plan['control']['cap'] == 255 and values[0] == 0.2, 'Wrong control cap/first value')
    require(plan['control']['max_simulated_seconds'] == len(values)*plan['model']['timestep_seconds'] == 2.0,
            'Simulation time budget differs')
    require(plan['control']['clock_tolerance_seconds'] == 1e-9, 'Clock tolerance changed')
    require(len(inputs['configurations']) == 5, 'Wrong reference configurations')
    return dict(commands=len(values), first=values[0], last=values[-1], reference_configurations=5,
                maximum_simulated_seconds=plan['control']['max_simulated_seconds'])


def semantics_check(plan):
    import grasp_process
    from manipulator_grasp.env.ur5_grasp_env import UR5GraspEnv
    prefix = PROJECT / 'qualified_closure_reachability_v1/run/source_snapshot'
    for obj, filename in ((UR5GraspEnv, 'ur5_grasp_env.py'), (grasp_process, 'grasp_process.py')):
        require(sha(Path(inspect.getfile(obj))) == sha(prefix / filename), 'Step/closure source changed')
    source = (prefix / 'ur5_grasp_env.py').read_text(encoding='utf-8')
    require('sm.SE3.Trans(0.0, 0.0, 0.13)' in source, 'Tool translation source changed')
    require(plan['tcp_local_translation_m'] == [0, 0, 0.13], 'Tool translation differs')
    action = dict(region='center', depth_mm=15, tilt_deg=30, azimuth_deg=135, symmetry_deg=180)
    require(plan['action'] == action and plan['seed'] == 978505, 'Frozen action differs')
    require(plan['source'] == read(PROJECT / plan['model']['metadata'])['source'], 'Wrong source object')
    observed = read(PROJECT / 'qualified_scene_model_diagnostic_v1/run/result.json')['observation']
    require(observed['observation_qualified'] is False, 'Observation history changed')
    require(plan['observation'] == dict(accepted=False, new_capture=0, model_calls=0,
                                       rejected_images_as_model_input=False), 'Visual protocol changed')
    require(read(PROJECT / 'qualified_closure_dynamics_v4/run/claim.json')['consumed'] == 1, 'Old claim changed')
    return dict(native_step_source_matches=True, closure_source_matches=True, old_claim_consumed=1,
                observation_qualified=False, production_gate='rejected/gripper_closure')
