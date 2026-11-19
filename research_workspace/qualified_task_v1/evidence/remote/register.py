from copy import deepcopy
from reflection.__main__ import bootstrap
bootstrap()
from observation_search_v1.common import verify as prior
from qualified_task_v1.common import ROOT, PROJECT, RUN, SEEDS, PILOT, read, save, sha


def main():
    old = prior()
    template = read(PROJECT/'surface_physical_v1/trial/manifest.json')['entry']['case']
    identities = dict(old['identities'])
    cases = {}
    for seed in SEEDS:
        path = PROJECT/f'observation_search_v1/run/{seed}/adaptive/views.json'
        view = read(path)[0]
        assert view['full_frame_qualified']
        case = deepcopy(template)
        case['config'] = deepcopy(old['configs'][str(seed)])
        case['config']['camera'] = view['camera']
        case['item'].update(id=f'qualified_task_{seed}', seed=seed, split='qualified_development_subset')
        cases[str(seed)] = case
        identities[str(path)] = sha(path)
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')]
    paths += [PROJECT/'observation_search_v1/run/manifest.json',
              PROJECT/'surface_physical_v1/trial/manifest.json']
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'manifest.json', dict(cases=cases, pilot=list(PILOT), identities=identities,
        scope='user_authorized_qualified_subset_initial_observation_preflight',
        old_general_integration_gate=False, camera_search_budget=0, max_task_attempts=0,
        max_model_calls=0, max_training_runs=0, independent_test_set=False))
    print(dict(registered=len(cases), pilot=PILOT, physical_attempts=0), flush=True)


if __name__ == '__main__':
    main()
