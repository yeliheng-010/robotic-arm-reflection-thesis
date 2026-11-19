"""批量扩到其他目标容器前，独立检查无故障可执行性。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from stability.experiment import OUT, SOURCES, THREADS, fingerprint, run


def configuration():
    return {'tasks': [dict(source=s, destination=d, fault='none', seed=7000)
                      for s in SOURCES for d in ('RedBin', 'SortingTray')],
            'arms': ['stable'], 'fingerprint': fingerprint(), 'threads': THREADS,
            'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'purpose': 'No-fault destination feasibility only; no training samples or tuning'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', action='store_true')
    args = parser.parse_args()
    config, directory = configuration(), OUT/'target_smoke_v1'
    assert all(os.environ.get(k) == v for k, v in THREADS.items())
    manifest = directory/'manifest.json'
    if args.freeze:
        directory.mkdir(exist_ok=True)
        with manifest.open('x') as stream:
            json.dump(config, stream, indent=2)
        return
    assert json.loads(manifest.read_text()) == config
    run(config, directory)
    rows = json.loads((directory/'result.json').read_text())
    report = {'tasks': len(rows), 'success': sum(r['success'] for r in rows),
              'first_success': sum(r['first_success'] for r in rows),
              'all_successful': len(rows) == 8 and all(r['success'] for r in rows),
              'training_samples': 0, 'slurm_job': os.environ.get('SLURM_JOB_ID')}
    (directory/'verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
