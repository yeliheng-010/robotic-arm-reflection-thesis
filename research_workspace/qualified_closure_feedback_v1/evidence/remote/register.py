"""冻结已有合格观测、动作范围和新预算；尚不开放物理执行。"""
from qualified_closure_feedback_v1.common import ROOT, PROJECT, RUN, SEED, read, save, sha


def main():
    from qualified_execution_v1.closeout import verify_inputs
    from qualified_closure_v2.common import verify as closure_verify
    verify_inputs()
    closure = closure_verify()
    old = PROJECT / 'qualified_execution_v1/run'
    identities = dict(read(old / 'execution_manifest.json')['identities'])
    identities.update(closure['originals'])
    identities.update(closure['sources'])
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sh', '.sbatch')]
    paths += [PROJECT / f'qualified_closure_v2/run/{name}.json'
              for name in ('closure', 'audit', 'positive', 'delivery_inventory')]
    paths += [old / 'attempt_claim.json', old / 'physical/result.json']
    for module in ('qualified_closure_v1', 'qualified_closure_v2'):
        paths += list((PROJECT / module).glob('*.py'))
    initial = PROJECT / f'qualified_task_v1/run/initial_v2/{SEED}/initial_observation'
    assert read(initial / 'qualification.json')['accepted']
    paths += [p for p in initial.rglob('*') if p.is_file()]
    from qualified_closure_feedback_v1.inputs import context
    request = context(SEED)['original']
    paths += [__import__('pathlib').Path(request['image'])]
    identities.update({str(p): sha(p) for p in paths})
    assert all(sha(p) == digest for p, digest in identities.items())
    save(RUN / 'manifest.json', dict(seed=SEED, identities=identities, max_model_calls=2,
         max_planning_sessions=2, conditional_max_physical_attempts=1,
         physical_execution_registered=False, max_training_runs=0, max_camera_search=0,
         repeated_invalid_stop_ends_budget=True, previous_attempt_claim_preserved=True))
    print(dict(registered=True, model_budget=2, physical_registered=False), flush=True)


if __name__ == '__main__':
    main()
