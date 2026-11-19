import os
from pathlib import Path
from f_response import validate, finish
from vs_common import ROOT, read, save, sha, verify


def inspect(item, mode, *, ready):
    key = item['condition']+'_'+mode+'_1'
    bundle = read(item['path'])
    folder = ROOT/'service/requests'
    assert read(folder/(key+'_request.json')) == dict(condition=item['condition'], mode=mode, ordinal=1,
        request=bundle['request'], messages=bundle[mode+'_messages'], visual=bundle['visual'])
    event = read(folder/(key+'_response.json'))
    assert event['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert event['encoding'] == read(folder/(key+'_generation_started.json'))['encoding']
    response = event['response']
    assert response['identity'] == ready['identity'] and not response['identity']['adapter_enabled']
    assert response['finish_reason'] == finish(response['generated_ids'], response['eos_ids'])
    encoding = event['encoding']
    grids = encoding['image_grid_thw']
    assert len(grids) == 2 and all(len(g) == 3 and min(g) > 0 for g in grids)
    assert encoding['pixel_values_shape'][0] == sum(g[0]*g[1]*g[2] for g in grids)
    assert encoding['input_tokens'] == response['prompt_tokens']
    saved = read(ROOT/'results'/(key+'.json'))
    assert saved['event'] == event and saved['validation'] == validate(response, bundle['request'], mode=mode)
    return dict(condition=item['condition'], mode=mode, validation=saved['validation'], encoding=encoding)


def main():
    assert os.environ.get('SLURM_JOB_ID') and not (ROOT/'audit.json').exists()
    manifest = verify()
    complete, ready = read(ROOT/'complete.json'), read(ROOT/'service/ready.json')
    assert ready['startup_generations'] == 0 and ready['manifest_sha256'] == sha(ROOT/'manifest.json')
    assert complete['model_calls'] == read(ROOT/'service/stopped.json')['calls'] == manifest['max_calls'] == 4
    assert read(ROOT/'service_exit.json') == dict(code=0, forced=False)
    folder = ROOT/'service/requests'
    for suffix in ('request', 'generation_started', 'response'):
        assert len(list(folder.glob('*_'+suffix+'.json'))) == 4
    assert not list(folder.glob('*_error.json'))
    rows = [inspect(item, mode, ready=ready) for item in manifest['inputs'] for mode in ('direct', 'diagnostic')]
    assert complete['valid'] == sum(r['validation']['valid'] for r in rows)
    artifacts = list(folder.glob('*.json')) + list((ROOT/'results').glob('*.json'))
    artifacts += [Path(__file__), ROOT/'complete.json', ROOT/'manifest.json']
    save(ROOT/'audit.json', dict(passed=True, rows=rows, model_calls=4, physical_attempts=0,
        training_ready=False, causal_correctness_not_established=True, identities={str(p):sha(p) for p in artifacts}))
    print(dict(passed=True, model_calls=4, valid=complete['valid']), flush=True)


if __name__ == '__main__':
    main()
