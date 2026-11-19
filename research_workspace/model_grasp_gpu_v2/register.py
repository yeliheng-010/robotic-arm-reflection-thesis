from model_grasp_gpu_v1.common import PROJECT, read, save, sha
from model_grasp_gpu_v2.scope import ROOT, BUDGET


def main():
    old = PROJECT/'model_grasp_gpu_v1'
    previous = read(old/'run/result.json')
    assert previous['used']['decisions'] == 1 and previous['real_model_calls'] == 0
    assert previous['planning_callbacks'] == previous['physical_attempts'] == 0
    manifest = read(old/'manifest.json')
    identities = dict(manifest['identities'])
    for path in ROOT.iterdir():
        if path.suffix in ('.py','.sh','.sbatch','.md'):
            identities[str(path)] = sha(path)
    identities[str(old/'run/result.json')] = sha(old/'run/result.json')
    for name in ('observation.json','preflight.json'):
        with (ROOT/name).open('xb') as stream:
            stream.write((old/name).read_bytes())
        identities[str(ROOT/name)] = sha(ROOT/name)
    manifest.update(identities=identities,budget=BUDGET,previous_decisions_consumed=1,
                    cumulative_decision_cap=4,revision='bounded_model_input_v2')
    save(ROOT/'manifest.json',manifest)
    print(dict(registered=True,remaining_budget=BUDGET,prior_decisions=1),flush=True)


if __name__ == '__main__':
    main()
