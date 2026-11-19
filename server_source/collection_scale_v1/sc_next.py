"""只在完整审计/导出后提交下一批；部分提交保留账本。"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from collection_common import ROOT as COLLECTION, read, save, sha, verify
from sc_policy import next_step

ROOT = Path(__file__).resolve().parent
DATASET = ROOT.parent/'recovery_dataset_v1'


def submit(script, folder, *, dependency=None, batch, export_job=None):
    variables = f'ALL,RECOVERY_BATCH={batch}'
    if export_job:
        variables += ',RECOVERY_EXPORT_JOB='+export_job
    command = ['sbatch','--parsable','--export='+variables]
    if dependency:
        command.append('--dependency=afterok:'+dependency)
    result = subprocess.run(command+[str(script)],check=True,capture_output=True,text=True)
    job = result.stdout.strip().split(';')[0]
    assert re.fullmatch(r'\d+',job), result.stdout
    save(folder/(script.stem+'_submitted.json'),dict(job=job,command=command+[str(script)]))
    return job


def history():
    rows = []
    for path in sorted(COLLECTION.glob('batches/*/physics/inventory.json')):
        inventory = verify(path)
        parts = inventory['summary']
        rows.append(dict(batch=int(path.parents[1].name), snapshots=sum(p['snapshots'] for p in parts.values()),
            recoveries=parts['train']['recoveries'], action_types=parts['train']['correction_action_types'],
            tasks=parts['train']['tasks']))
    return rows


def main():
    assert os.environ.get('SLURM_JOB_ID')
    export_job = os.environ['RECOVERY_EXPORT_JOB']
    assert re.fullmatch(r'\d+',export_job)
    output = DATASET/'exports'/('job_'+export_job)
    data = verify(output/'manifest.json')
    assert all(sha(output/p)==h for p,h in data['outputs'].items())
    rows = history()
    assert len(rows)==len(data['batches'])
    decision = next_step(rows,quantitative_ready=data['gate']['quantitative_ready'])
    free_bytes = shutil.disk_usage(COLLECTION).free
    if decision['advance'] and free_bytes < 20*1024**3:
        decision = dict(advance=False,reason='less_than_20_GiB_free_before_next_batch')
    folder = ROOT/'decisions'/f'after_batch_{len(rows)-1:03d}'
    save(folder/'decision.json',dict(decision=decision,history=rows,source=str(output/'manifest.json'),
        source_sha256=sha(output/'manifest.json'),training_started=False,free_bytes=free_bytes))
    print(decision,flush=True)
    if not decision['advance']:
        return
    batch = decision['batch']
    prepared = submit(ROOT/'prepare.sbatch',folder,batch=batch)
    qualified = submit(ROOT/'shards.sbatch',folder,batch=batch,dependency=prepared)
    merged = submit(ROOT/'merge.sbatch',folder,batch=batch,dependency=qualified)
    physical_ready = submit(ROOT/'physical_prepare.sbatch',folder,batch=batch,dependency=merged)
    physical = submit(ROOT/'physical_shards.sbatch',folder,batch=batch,dependency=physical_ready)
    collected = submit(ROOT/'physical_merge.sbatch',folder,batch=batch,dependency=physical)
    exported = submit(DATASET/'export.sbatch',folder,batch=batch,dependency=collected)
    submit(ROOT/'next.sbatch',folder,batch=batch,dependency=exported,export_job=exported)


if __name__=='__main__':
    main()
