"""静态证明直达分支不变的条件复用；仅执行改了路径的条件。"""
from pathlib import Path
from copy import deepcopy
from cc_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
REPAIR = ROOT/'repair'
SOURCE = ROOT.parent/'task_accuracy_v1/pilot'
PROBE = ROOT/'probes/job_6405/result.json'


def main():
    assert not REPAIR.exists()
    source, probe = verify(SOURCE/'manifest.json'), verify(PROBE)
    assert probe['all_admissible']
    identities = dict(source['identities'], **probe['identities'])
    identities.update({str(p): sha(p) for p in (SOURCE/'manifest.json', SOURCE/'result.json', PROBE)})
    changed = {r['seed'] for r in probe['rows'] if r['result']['selected']['id'] != 'direct'}
    cases = [c for c in source['cases'] if c['item']['seed'] in changed]
    for seed in source['seeds']:
        audit = SOURCE/'audits'/(str(seed)+'.json')
        assert verify(audit)['passed']
        identities[str(audit)] = sha(audit)
    files = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')]
    identities.update({str(p): sha(p) for p in files})
    save(REPAIR/'manifest.json', dict(cases=cases, all_cases=source['cases'], identities=identities,
        changed_seeds=sorted(changed), reused_seeds=[s for s in source['seeds'] if s not in changed],
        max_new_attempts=len(cases), max_model_calls=0, training_updates=0,
        limitation='Unchanged direct-path conditions reused, not rerun'))
    for case in cases:
        seed = case['item']['seed']
        path = SOURCE/'qualification'/str(seed)/'result.json'
        qualification = deepcopy(read(path))
        qualification.update(manifest_sha256=sha(REPAIR/'manifest.json'),
            source_path=str(path), source_sha256=sha(path))
        save(REPAIR/'qualification'/str(seed)/'result.json', qualification)
    print(dict(changed=sorted(changed), reused=5-len(changed)), flush=True)


if __name__ == '__main__':
    main()
