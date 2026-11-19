import os
from pathlib import Path
from sd_common import read, save, sha
from live_session import run_once

ROOT = Path(__file__).resolve().parent


def verify():
    manifest = read(ROOT/'manifest.json')
    for path, digest in manifest['identities'].items():
        assert sha(path) == digest, path
    return manifest


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    rows = []
    for case in manifest['cases']:
        config = case['config']
        if not config['geometry_accepted'] or not config['compiled_check']['passed']:
            rows.append(dict(id=case['item']['id'], attempts=0, status='geometry_rejected'))
            continue
        rows.append(run_once(case, ROOT/'runs'/case['item']['id']))
        print(rows[-1], flush=True)
    verify()
    save(ROOT/'run_complete.json', dict(rows=rows, actual_new_attempts=sum(r['attempts'] for r in rows),
         model_calls=0, training_runs=0, manifest_sha256=sha(ROOT/'manifest.json')))


if __name__ == '__main__':
    main()
