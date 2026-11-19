"""监控已审计导出；训练始终通过后续独立门禁。"""
import os
import re
import subprocess
import time
import traceback
from pathlib import Path
from f_common import read, save, sha
from policy import decide

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
POLL_SECONDS = 30
MAX_SECONDS = 23 * 3600


def latest():
    paths = list((PARENT/'recovery_dataset_v1/exports').glob('job_*/manifest.json'))
    if not paths:
        return None, None, None
    path = max(paths, key=lambda p: int(p.parent.name.split('_')[1]))
    manifest = read(path)
    index = len(manifest['batches']) - 1
    decision = PARENT/'collection_scale_v1/decisions'/f'after_batch_{index:03d}'/'decision.json'
    value = read(decision)['decision'] if decision.exists() else None
    return path, manifest, value


def submit(output, *, stage, script, variables, dependencies=()):
    assert all(re.fullmatch(r'\d+', str(v)) for v in variables.values())
    command = ['sbatch', '--parsable', '--export=ALL,' + ','.join(f'{k}={v}' for k, v in variables.items())]
    if dependencies:
        assert all(re.fullmatch(r'\d+', job) for job in dependencies)
        command.append('--dependency=afterok:' + ':'.join(dependencies))
    command.append(str(PARENT/script))
    save(output/(stage+'_intent.json'), dict(command=command))
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    job = result.stdout.strip().split(';')[0]
    assert re.fullmatch(r'\d+', job), result.stdout
    save(output/(stage+'_submitted.json'), dict(command=command, job=job))
    print(dict(stage=stage, job=job), flush=True)
    return job


def transition(output, path):
    manifest = read(path)
    assert manifest['gate']['quantitative_ready']
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    assert all(sha(path.parent/p) == h for p, h in manifest['outputs'].items())
    variables = dict(RECOVERY_EXPORT_JOB=path.parent.name.split('_')[1])
    audit = submit(output, stage='audit', script='visual_dataset_audit_v1/audit.sbatch', variables=variables)
    prepare = submit(output, stage='comparison_prepare', script='visual_comparison_v1/prepare.sbatch',
        variables=variables)
    comparison = submit(output, stage='comparison', script='visual_comparison_v1/run.sbatch',
        variables=variables, dependencies=(prepare,))
    variables['VISUAL_DATASET_AUDIT_JOB'] = audit
    frozen = submit(output, stage='freeze', script='visual_finetune_v1/freeze.sbatch',
        variables=variables, dependencies=(audit, comparison))
    training = submit(output, stage='training', script='visual_finetune_v1/train.sbatch',
        variables=variables, dependencies=(frozen,))
    save(output/'chain_submitted.json', dict(export=str(path), export_sha256=sha(path),
        audit=audit, comparison=comparison, freeze=frozen, training=training,
        claim='submitted_with_dependencies_not_started_or_completed'))


def main():
    assert os.environ.get('SLURM_JOB_ID')
    output = ROOT/'runs'/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    frozen = read(ROOT/'source_manifest.json')
    assert all(sha(p) == h for p, h in frozen['identities'].items())
    previous, index, started = None, 0, time.monotonic()
    try:
        while time.monotonic() - started < MAX_SECONDS:
            path, manifest, decision = latest()
            state = dict(status=decide(manifest, decision), export=str(path), collection_decision=decision)
            if state != previous:
                save(output/'events'/f'{index:04d}.json', state)
                print(state, flush=True)
                previous, index = state, index + 1
            if state['status'] != 'collecting':
                assert all(sha(p) == h for p, h in frozen['identities'].items())
                if state['status'] == 'stage_preparation':
                    transition(output, path)
                save(output/'result.json', dict(state, goal_complete=False))
                return
            time.sleep(POLL_SECONDS)
        save(output/'result.json', dict(status='monitor_time_budget_reached', goal_complete=False))
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
