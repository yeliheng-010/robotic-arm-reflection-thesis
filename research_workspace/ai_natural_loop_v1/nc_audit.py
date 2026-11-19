"""只读审计单阶段；失败关闭下一阶段门禁，不补跑。"""
import argparse
import os
from nc_common import ROOT, METHODS, read, save, sha, verify
from nc_audit_branch import replay


def inspect(case):
    folder = ROOT/'cases'/case['item']['id']
    result = read(folder/'result.json')
    assert result['manifest_sha256'] == sha(ROOT/'manifest.json')
    if result['status'] == 'geometry_rejected':
        assert not case['config']['geometry_accepted'] or not case['config']['compiled_check']['passed']
        assert result['new_attempts'] == result['model_calls'] == 0 and result['methods'] == {}
        return dict(id=result['id'], status=result['status'], attempts=0, model_calls=0, methods={})
    assert result['status'] == 'completed' and set(result['methods']) == set(METHODS)
    first = read(folder/'first/step.json')
    first_view = read(folder/'first/observation_summary.json')
    assert first['state'] == case['state'] and first['index'] == 1
    methods, initial = {}, []
    attempts, calls, extra = 1, 0, 0
    for method in METHODS:
        branch = read(folder/method/'result.json')
        assert branch['method'] == method
        methods[method] = replay(case, branch, first=first, first_view=first_view)
        for key in ('success', 'new_attempts', 'model_calls', 'extra_observations', 'status'):
            assert branch[key] == result['methods'][method][key]
        attempts += branch['new_attempts']
        calls += branch['model_calls']
        extra += branch['extra_observations']
        if branch['decisions']:
            initial.append(read(branch['decisions'][0]['input_path'])['request'])
    assert not initial or len(initial) == 3 and initial[0] == initial[1] == initial[2]
    assert attempts == result['new_attempts'] <= 7 and calls == result['model_calls'] <= 8 and extra <= 6
    return dict(id=result['id'], status='completed', attempts=attempts, model_calls=calls, methods=methods)


def main():
    assert os.environ.get('SLURM_JOB_ID')
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, required=True)
    args = parser.parse_args()
    manifest = verify()
    cases = [c for c in manifest['cases'] if c['item']['seed'] == args.seed]
    assert len(cases) == 4
    rows = [inspect(case) for case in cases]
    verify()
    artifacts = [p for c in cases for p in (ROOT/'cases'/c['item']['id']).rglob('*') if p.is_file()]
    value = dict(passed=True, seed=args.seed, rows=rows, training_ready=False,
        attempts=sum(r['attempts'] for r in rows), model_calls=sum(r['model_calls'] for r in rows),
        identities={str(p): sha(p) for p in artifacts}, manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/f'audit_{args.seed}.json', value)
    print({k: v for k, v in value.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()
