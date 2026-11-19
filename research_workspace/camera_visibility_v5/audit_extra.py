import os
from sd_common import read, save, sha
from audit import ROOT, audit_case


def main():
    source = ROOT/'extra'/('job_'+os.environ['CV_EXTRA_JOB'])
    registered = read(source/'registered.json')
    assert read(source/'summary.json')['registration_sha256'] == sha(source/'registered.json')
    assert sha(registered['source']) == registered['source_sha256']
    output = ROOT/'extra_audits'/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    rows = [audit_case(source/str(c['item']['seed']), c['config'], output=output)
            for c in registered['cases']]
    files = [p for p in source.rglob('*') if p.is_file()]
    save(output/'result.json', dict(passed=True, rows=rows,
        identities={str(p): sha(p) for p in files}, physical_attempts=0, model_calls=0))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
