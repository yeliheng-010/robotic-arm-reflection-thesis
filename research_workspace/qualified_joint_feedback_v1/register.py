from qualified_joint_feedback_v1.common import ROOT, PROJECT, RUN, SEEDS, MAX_DECISIONS, read, save, sha


def main():
    identities = {}
    for folder in ('qualified_path_v1', 'qualified_feedback_v1'):
        source = PROJECT/folder/'run'
        audit = read(source/'audit_result.json')
        assert audit['passed']
        for name in ('manifest.json', 'audit_result.json'):
            old = read(source/name)['identities']
            assert all(sha(p) == h for p, h in old.items())
            identities.update(old)
        identities[str(source/'audit_result.json')] = sha(source/'audit_result.json')
    old = read(PROJECT/'qualified_path_v1/run/planning_manifest.json')['identities']
    assert all(sha(p) == h for p, h in old.items())
    identities.update(old)
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md')]
    for seed in SEEDS:
        paths += [PROJECT/f'qualified_model_v1/run/{seed}/{name}.json' for name in ('request', 'validated')]
        paths += [PROJECT/f'qualified_intent_v1/run/{seed}/observation.json',
            PROJECT/f'qualified_intent_v1/run_v3/{seed}/request.json',
            PROJECT/f'qualified_intent_v1/run_v3/{seed}/validated.json']
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'manifest.json', dict(identities=identities, seeds=SEEDS,
        max_decisions_per_layout=MAX_DECISIONS, max_model_calls=len(SEEDS)*MAX_DECISIONS,
        max_planning_sessions=len(SEEDS)*MAX_DECISIONS, planning_timeout_s=240,
        max_task_attempts=0, max_training_runs=0, max_camera_search=0,
        input_extension='Observed placement and prior model task grounding only',
        scope='Qualified development subset; not a controlled success-rate comparison'))
    print(dict(registered=True, model_budget=len(SEEDS)*MAX_DECISIONS), flush=True)


if __name__ == '__main__':
    main()
