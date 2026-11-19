"""仅使用指定正式导出的批次，报告筛选偏差和任务覆盖。"""
import json
import os
import re
from pathlib import Path
from collection_common import ROOT as COLLECTION, verify, sha, save
from rc_gate import summarize
from coverage_stats import stages, task_counts

ROOT = Path(__file__).resolve().parent


def load_source():
    export_job = os.environ['RECOVERY_EXPORT_JOB']
    assert re.fullmatch(r'\d+', export_job)
    folder = ROOT.parent/'recovery_dataset_v1/exports'/('job_' + export_job)
    path = folder/'manifest.json'
    manifest = verify(path)
    assert all(sha(folder/p) == h for p, h in manifest['outputs'].items())
    with (folder/'outcomes.jsonl').open(encoding='utf-8') as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    assert summarize(rows) == manifest['summary']
    identities = {str(path): sha(path), str(folder/'outcomes.jsonl'): sha(folder/'outcomes.jsonl')}
    return manifest, rows, identities


def load_cases(batches, identities):
    cases, qualified = [], set()
    for batch in batches:
        folder = COLLECTION/'batches'/f"{batch['batch']:03d}"/'qualification'
        path, result_path = folder/'manifest.json', folder/'result.json'
        manifest, result = verify(path), verify(result_path)
        assert result['manifest_sha256'] == sha(path)
        allowed = {r['id'] for r in result['rows'] if r['passed']}
        assert len(result['rows']) == len(manifest['cases']) == batch['proposed']
        assert len(allowed) == batch['qualified']
        cases.extend(manifest['cases'])
        qualified.update(allowed)
        identities.update({str(p): sha(p) for p in (path, result_path)})
    return cases, qualified


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
