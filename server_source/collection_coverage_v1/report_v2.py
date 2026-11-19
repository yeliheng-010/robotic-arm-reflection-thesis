"""使用分解后的纯统计函数；保留原只读加载和输出约定。"""
import os
import re
from report import ROOT, load_source, load_cases, sha, save
from coverage_stats_v2 import stages, task_counts


def main():
    job = os.environ['SLURM_JOB_ID']
    assert re.fullmatch(r'\d+', job)
    manifest, rows, identities = load_source()
    cases, qualified = load_cases(manifest['batches'], identities)
    result = dict(summary=manifest['summary'], gate=manifest['gate'],
        by_task=task_counts(rows), stages=stages(cases, qualified, rows),
        quantitative_gate_unchanged=True, physical_attempts=0, model_calls=0,
        training_updates=0, identities=identities,
        limitation='Descriptive selected-data coverage; not uniformity, causality or generalization evidence')
    result['identities'].update({str(p): sha(p) for p in ROOT.iterdir()
        if p.suffix in ('.py', '.sbatch', '.md')})
    save(ROOT/'results'/('job_' + job + '.json'), result)
    print(dict(by_task=result['by_task'], quantitative_ready=manifest['gate']['quantitative_ready']), flush=True)


if __name__ == '__main__':
    main()
