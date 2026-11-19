import argparse
import os
from nc_common import ROOT, METHODS, save, sha, verify
from nc_session import opened
from nc_observation import View
from nc_branch import run


def execute(case):
    folder = ROOT/'cases'/case['item']['id']
    folder.mkdir(parents=True, exist_ok=False)
    if not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']:
        save(folder/'result.json', dict(id=case['item']['id'], status='geometry_rejected', new_attempts=0,
             methods={}, model_calls=0, manifest_sha256=sha(ROOT/'manifest.json')))
        return
    rows = {}
    with opened(case, case['state'], folder=folder/'first', index=1) as first:
        view = View(first, folder=folder/'first/observations', remaining=2)
        save(folder/'first/observation_summary.json', view.summary())
        for method in METHODS:
            value = run(case, first, shared=view, method=method, folder=folder/method)
            rows[method] = dict(success=value['success'], new_attempts=value['new_attempts'],
                model_calls=value['model_calls'], extra_observations=value['extra_observations'], status=value['status'])
            print(case['item']['id'], method, rows[method], flush=True)
    result = dict(id=case['item']['id'], status='completed', methods=rows,
        new_attempts=1+sum(r['new_attempts'] for r in rows.values()),
        model_calls=sum(r['model_calls'] for r in rows.values()), manifest_sha256=sha(ROOT/'manifest.json'))
    assert result['new_attempts'] <= 7 and result['model_calls'] <= 8
    save(folder/'result.json', result)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('case_id')
    args = parser.parse_args()
    manifest = verify()
    case = next(r for r in manifest['cases'] if r['item']['id'] == args.case_id)
    execute(case)
    verify()


if __name__ == '__main__':
    main()
