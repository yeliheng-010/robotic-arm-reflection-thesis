"""仅重渲染三个已用开发布局；不调用模型或搬运执行器。"""
import os
from pathlib import Path
from sd_common import read, save, sha
from cv_select import select

ROOT = Path(__file__).resolve().parent
CASES = (('003', 964103), ('009', 964294), ('009', 964306))


def main():
    job = os.environ['SLURM_JOB_ID']
    output = ROOT/'runs'/('job_'+job)
    output.mkdir(parents=True, exist_ok=False)
    sources = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch')}
    rows = []
    for batch, seed in CASES:
        path = ROOT.parent/'recovery_collection_v1/batches'/batch/'physics/manifest.json'
        sources[str(path)] = sha(path)
        case = next(c for c in read(path)['cases'] if c['item']['id'] == f'R0_{seed}_varied_noisy')
        config, result = select(case['config'], output/str(seed))
        if config:
            assert {k: v for k, v in config.items() if k != 'camera'} == {
                k: v for k, v in case['config'].items() if k != 'camera'}
        row = dict(seed=seed, accepted=result['accepted'], proposals=len(result['attempts']),
                   selected_index=result['attempts'][-1]['index'] if config else None)
        rows.append(row)
        print(row, flush=True)
    assert all(sha(p) == h for p, h in sources.items())
    save(output/'summary.json', dict(complete=True, rows=rows, identities=sources,
        physical_attempts=0, model_calls=0, training_updates=0, test_used=False,
        scope='used-development-layout camera-only validation'))


if __name__ == '__main__':
    main()
