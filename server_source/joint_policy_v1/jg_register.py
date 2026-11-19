"""固定回归输入与已有成功证据；禁止新挑种子或重跑物理任务。"""
from pathlib import Path
from cc_common import read,save,sha,verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
RUN = ROOT/'regression'
OLD_SEEDS = (964008,964009,964012,964294,964306)


def row(base, case, *, name, successful):
    folder = base/'cases'/str(case['item']['seed'])/'first'
    return dict(name=name,case=case,folder=str(folder),plan=str(folder/'route.json'),
                successful=successful)


def registrations():
    cases = read(PARENT/'task_accuracy_v1/pilot/manifest.json')['cases']
    rows = []
    for seed in OLD_SEEDS:
        base = PARENT/('return_home_v1/repair' if seed==964009 else 'task_accuracy_v1/pilot')
        case = next(c for c in cases if c['item']['seed']==seed)
        rows.append(row(base,case,name='old_'+str(seed),successful=True))
    base = PARENT/'fresh_accuracy_v1/run/conditions/F0_964347_varied_noisy/improved'
    rows.append(row(base,read(base/'manifest.json')['cases'][0],name='new_964347',successful=True))
    base = PARENT/'joint_representation_v1/trial_gpu'
    rows.append(row(base,read(base/'manifest.json')['cases'][0],name='new_964345',successful=True))
    for seed in (964345,964347):
        folder = PARENT/'qualification_strategy_v1/actual/cases'/f'F1_{seed}_varied_noisy'
        rows.append(dict(name='capsule_'+str(seed),case=verify(folder/'result.json')['case'],
            folder=str(folder),plan=str(folder/'actual_plan.json'),successful=False))
    return rows


def main():
    assert not RUN.exists()
    prior = verify(PARENT/'joint_representation_v1/trial_gpu/manifest.json')
    rows = registrations()
    paths = [*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    for entry in rows:
        folder = Path(entry['folder'])
        paths.extend([Path(entry['plan']),folder/'span_inputs.npz',folder/'span_guard.json'])
        if entry['successful']:
            step = read(folder/'step.json')
            assert step['success']
            paths.append(folder/'step.json')
    identities = dict(prior['identities'])
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=rows,identities=identities,physical_attempts=0,model_calls=0))


if __name__ == '__main__':
    main()
