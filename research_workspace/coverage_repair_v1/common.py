from pathlib import Path
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent


def prepare():
    old = PARENT/'oriented_transfer_v1/endpoints/manifest.json'
    previous = verify(old)
    entry = next(r for r in previous['rows'] if r['name']=='capsule_964347')
    fresh = PARENT/'fresh_accuracy_v1/run/manifest.json'
    current = verify(fresh)
    terminal = PARENT/'oriented_transfer_v1/trial_gpu_v3/manifest.json'
    done = verify(terminal)
    rows = [dict(name=f'initial_{seed}',config=next(c['config'] for c in current['cases']
        if c['item']['seed']==seed),selection=str(fresh.parent/'cameras'/str(seed)/'selection.json'))
        for seed in (964346,964348)]
    report = terminal.parent/'cases/964345/first/observations/visibility_0.json'
    rows.append(dict(name='terminal_964345',config=done['entry']['case']['config'],snapshot=str(report)))
    identities = dict(previous['identities'])
    identities.update(current['identities'])
    identities.update(done['identities'])
    paths = [old,fresh,terminal,report,Path(read(report)['state_path']),
        *[Path(r['selection']) for r in rows if 'selection' in r]]
    paths += [p for p in ROOT.iterdir() if p.suffix in ('.py','.sh','.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(ROOT/'manifest.json',dict(entry=entry,rows=rows,identities=identities,
        max_new_grasp_poses=128,max_new_cameras_per_state=128,
        physical_attempts=0,model_calls=0,training_updates=0,private_engineering_only=True))
