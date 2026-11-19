"""预登记首六个不同种子开发布局；全部保留，不按成功换样本。"""
import os
from pathlib import Path
from sd_common import read, save, sha
from cv_select import select

ROOT = Path(__file__).resolve().parent
CASE_LIMIT = 6


def main():
    output = ROOT/'extra'/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    path = ROOT.parent/'recovery_collection_v1/batches/000/physics/manifest.json'
    candidates = [c for c in read(path)['cases'] if c['item']['group'] == 'varied_noisy']
    unique = {}
    for case in sorted(candidates, key=lambda c: c['item']['id']):
        unique.setdefault(case['item']['seed'], case)
    cases = list(unique.values())[:CASE_LIMIT]
    save(output/'registered.json', dict(cases=cases, source=str(path), source_sha256=sha(path),
        max_candidates=CASE_LIMIT*256, physical_attempts=0, test_used=False))
    rows = []
    for case in cases:
        seed = case['item']['seed']
        config, result = select(case['config'], output/str(seed))
        row = dict(seed=seed, accepted=result['accepted'], proposals=len(result['attempts']),
                   selected_index=result['attempts'][-1]['index'] if config else None)
        rows.append(row)
        print(row, flush=True)
    save(output/'summary.json', dict(complete=True, rows=rows, physical_attempts=0,
        model_calls=0, training_updates=0, registration_sha256=sha(output/'registered.json')))


if __name__ == '__main__':
    main()
