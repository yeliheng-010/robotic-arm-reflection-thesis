import os
from qualified_closure_reachability_v1.common import ROOT, RUN, PARENT, CODE, read, save, sha


def main():
    assert os.environ.get('SLURM_JOB_ID')
    prior = read(PARENT / 'run/manifest.json')
    identities = dict(prior['identities'])
    inventory = read(PARENT / 'run/delivery_inventory.json')
    assert inventory['passed'] and read(PARENT / 'run/audit_result.json')['passed']
    assert read(PARENT / 'run/result.json')['stage'] == 'gripper_closure'
    identities.update({str(PARENT / name): digest for name, digest in inventory['identities'].items()})
    for name, expected in identities.items():
        assert sha(name) == expected, name
    closure = read(PARENT / 'run/preflight/closure.json')
    rows = [dict(index=i, saved=row) for i, row in enumerate(closure['envelope']) if row['valid'] and row['contacts']]
    assert len(rows) == 5
    save(RUN / 'input.json', dict(command=closure['command'], configurations=rows,
         parent_closure_sha256=sha(PARENT / 'run/preflight/closure.json')))
    sources = {'2f85.xml': CODE / 'manipulator_grasp/assets/robotiq_2f85/2f85.xml',
               'grasp_process.py': CODE / 'grasp_process.py',
               'ur5_grasp_env.py': CODE / 'manipulator_grasp/env/ur5_grasp_env.py'}
    for name, source in sources.items():
        assert identities[str(source)] == sha(source)
        target = RUN / 'source_snapshot' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(source.read_bytes())
        identities[str(target)] = sha(target)
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch')]
    paths += [RUN / 'input.json', PARENT / 'run/delivery_inventory.json']
    identities.update({str(path): sha(path) for path in paths})
    save(RUN / 'manifest.json', dict(identities=identities, fixed_configurations=5,
         max_diagnostic_runs=1, max_model_calls=0, max_physical_attempts=0, max_training_runs=0,
         dynamic_reachability_proof=False, safety_gate_changes=False, input_sha256=sha(RUN / 'input.json')))
    print(dict(registered=True, identities=len(identities), fixed_configurations=5), flush=True)


if __name__ == '__main__':
    main()
