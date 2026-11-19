import argparse
import os
from reflection.__main__ import bootstrap
bootstrap()
from sv_common import ROOT, METHODS, read, save, sha, verify
from sv_audit_replay import replay


def inspect(case):
    folder = ROOT/'cases'/case['item']['id']
    result = read(folder/'result.json')
    assert result['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert result['status'] == 'completed' and set(result['methods']) == set(METHODS)
    first, observed = read(folder/'first/step.json'), read(folder/'first/observation_summary.json')
    assert first['state'] == case['state'] and first['index'] == 1
    methods, initial, cache = {}, [], {}
    attempts, calls, extra = 1, 0, 0
    for method in METHODS:
        branch = read(folder/method/'result.json')
        assert branch['method'] == method
        methods[method] = replay(case, branch, first=first, first_view=observed, cache=cache)
        for key in ('success', 'new_attempts', 'model_calls', 'extra_observations', 'status'):
            assert branch[key] == result['methods'][method][key]
        attempts += branch['new_attempts']
        calls += branch['model_calls']
        extra += branch['extra_observations']
        if branch['decisions']:
            bundle = read(branch['decisions'][0]['input_path'])
            initial.append((bundle['request'], bundle['visual']))
    assert not initial or len(initial) == 3 and initial[0] == initial[1] == initial[2]
    assert attempts == result['new_attempts'] <= 7 and calls == result['model_calls'] <= 8 and extra <= 6
    return dict(id=case['item']['id'], attempts=attempts, model_calls=calls, methods=methods,
        physical=[dict(path=p, geometry=v['geometry'], contact=v['contact']) for p,v in cache.items()])


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('--case-id', required=True)
    name = parser.parse_args().case_id
    case = next(c for c in verify()['cases'] if c['item']['id'] == name)
    row = inspect(case)
    files = [p for p in (ROOT/'cases'/name).rglob('*') if p.is_file()]
    save(ROOT/'audits'/(name+'.json'), dict(passed=True, row=row, training_ready=False,
        manifest_sha256=sha(ROOT/'manifest.json'), identities={str(p):sha(p) for p in files}))
    print(dict(id=name, attempts=row['attempts'], model_calls=row['model_calls']), flush=True)


if __name__ == '__main__':
    main()
