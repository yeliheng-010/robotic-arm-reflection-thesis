"""冻结失败版本后，仅登记原授权剩余的一次真实生成。"""
import os
from qualified_prompt_checkpoint_v1.protocol import verify as verify_original
from qualified_prompt_checkpoint_v2.common import ROOT, PROJECT, RUN, PRIOR, read, save, sha, prior_zero_generation


def main():
    assert os.environ.get('SLURM_JOB_ID')
    prior = prior_zero_generation()
    identities = dict(verify_original()['identities'])
    paths = [p for p in PRIOR.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    paths += [p for p in ROOT.iterdir() if p.suffix in ('.py', '.sh', '.sbatch', '.md', '.json')]
    identities.update({str(p): sha(p) for p in paths})
    RUN.mkdir(parents=True, exist_ok=True)
    with (RUN / 'request.json').open('xb') as stream:
        stream.write((PRIOR / 'run/request.json').read_bytes())
    assert sha(RUN / 'request.json') == sha(PRIOR / 'run/request.json')
    identities[str(RUN / 'request.json')] = sha(RUN / 'request.json')
    save(RUN / 'manifest.json', dict(max_model_calls=1, max_planning=0, max_physical=0, max_training=0,
         seed=978505, identities=identities, prior_model_reservations=1, prior_actual_generations=0,
         total_authorized_actual_generations=1, prior_failure_audit_sha256=sha(PRIOR / 'run/failure_audit.json'),
         baseline_request=read(PRIOR / 'run/manifest.json')['baseline_request'],
         request_sha256=sha(RUN / 'request.json'), identical_to_pre_generation_request=True,
         registration_job=os.environ['SLURM_JOB_ID']))
    print(dict(registered=True, identities=len(identities), prior_actual_generations=prior['model_calls'],
               remaining_actual_generations=1), flush=True)


if __name__ == '__main__':
    main()
