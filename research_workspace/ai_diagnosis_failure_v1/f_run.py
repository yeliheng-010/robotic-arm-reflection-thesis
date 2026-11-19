import os
from f_common import ROOT, save, sha, verify
from f_session import run_once


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'execution_started.json', dict(max_new_attempts=1, job=os.environ['SLURM_JOB_ID']))
    row = run_once(manifest['case'], ROOT/'run')
    verify()
    save(ROOT/'run_complete.json', dict(row, manifest_sha256=sha(ROOT/'manifest.json')))
    print(row, flush=True)


if __name__ == '__main__':
    main()
