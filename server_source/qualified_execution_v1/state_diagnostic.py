"""只读重建保存末态，列出原审计差异；不放宽完全相等断言。"""
from types import SimpleNamespace
import numpy as np
import mujoco
from qualified_execution_v1.environment import opened, state
from qualified_execution_v1.common import ROOT, RUN, read, save, sha, verify, case
from qualified_execution_v1.audit import paths
from qualified_execution_v1.contact_audit import restored, contacts
from qualified_execution_v1.policy import accepted
from reflection.monitors import evaluate_placement


def differences(recorded, rebuilt):
    assert recorded.keys() == rebuilt.keys()
    rows = {}
    for key, old in recorded.items():
        new = rebuilt[key]
        if old == new:
            continue
        row = dict(recorded=old, rebuilt=new)
        if isinstance(old, (float, list)):
            row['max_absolute_difference'] = float(np.max(np.abs(np.asarray(new)-np.asarray(old))))
        rows[key] = row
    return rows


def evaluate(model, data, item, initial_quat):
    env = SimpleNamespace(mj_model=model, mj_data=data)
    physical, evidence, _ = evaluate_placement(env, item['source'], item['destination'], initial_quat)
    return dict(physical_placement=bool(physical), evaluation=evidence)


def inspect(env, item, recorded):
    folder, model = RUN/'physical', env.mj_model
    with np.load(folder/'final_state.npz') as values:
        final = values['state'].copy()
    with np.load(folder/'final_observation/source_state.npz') as values:
        np.testing.assert_array_equal(final, values['state'])
    first, second = restored(model, final), restored(model, final)
    quat = np.asarray(read(folder/'initial_quat.json'))
    rebuilt = evaluate(model, first, item, quat)
    assert rebuilt == evaluate(model, second, item, quat)
    before_qpos, before_qvel = first.qpos.copy(), first.qvel.copy()
    mujoco.mj_forward(model, first)
    assert rebuilt == evaluate(model, first, item, quat)
    np.testing.assert_array_equal(before_qpos, first.qpos)
    np.testing.assert_array_equal(before_qvel, first.qvel)
    delta = differences(recorded['evaluation'], rebuilt['evaluation'])
    success = accepted(completed=recorded['completed'], physical_placement=rebuilt['physical_placement'],
        safety_error=recorded['safety_error'])
    source = first.body(item['source'])
    joint = model.body_jntadr[source.id]
    adr = model.jnt_qposadr[joint]
    return dict(rebuilt=rebuilt, differences=delta, final_evaluation_identical=not delta,
        physical_verdict_identical=rebuilt['physical_placement'] == recorded['physical_placement'],
        task_verdict_identical=success == recorded['success'], rebuilt_success=success,
        repeated_forward_evaluation_identical=True, final_observation_state_identical=True,
        actual_contacts=contacts(model, first, item), source_free_joint_qpos=first.qpos[adr:adr+7].tolist(),
        timestep_s=float(model.opt.timestep), time_s=float(first.time),
        original_cached_derived_state_saved=False, cache_timing_cause_proven=False)


def main():
    verify()
    folder, item = RUN/'physical', case()
    frozen = {str(p): sha(p) for p in folder.rglob('*') if p.is_file()}
    save(RUN/'state_diagnostic_manifest.json', dict(identities=frozen,
        source_sha256=sha(ROOT/'state_diagnostic.py')))
    with opened(item, {}, static=True) as env:
        before = state(env)
        rebuilt_paths = paths(item, read(folder/'private_paths.json'))
        result = inspect(env, item['item'], read(folder/'result.json'))
        np.testing.assert_array_equal(before, state(env))
    assert all(sha(p) == h for p, h in frozen.items())
    verify()
    result.update(paths=rebuilt_paths, physical_attempts=0, model_calls=0, training_runs=0,
        original_audit_replaced=False, original_thresholds_unchanged=True)
    save(RUN/'state_diagnostic.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main()
