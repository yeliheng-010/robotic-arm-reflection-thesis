import json
import os
import subprocess
import urllib.request
from unittest.mock import patch
import nc_controller
from f_response import validate, finish
from vs_common import ROOT, PORT, read, save, verify


def generate(item, mode):
    bundle = read(item['path'])
    body = dict(condition=item['condition'], mode=mode, ordinal=1, request=bundle['request'],
        messages=bundle[mode+'_messages'], visual=bundle['visual'])
    request = urllib.request.Request(f'http://127.0.0.1:{PORT}/generate',
        data=json.dumps(body, ensure_ascii=False, allow_nan=False).encode(),
        headers={'Content-Type': 'application/json'})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(request, timeout=300) as response:
        event = json.load(response)
    assert event == read(ROOT/'service/requests'/(event['id']+'_response.json'))
    generated = event['response']
    assert not generated['identity']['adapter_enabled']
    assert generated['finish_reason'] == finish(generated['generated_ids'], generated['eos_ids'])
    assert len(event['encoding']['image_grid_thw']) == 2
    result = dict(condition=item['condition'], mode=mode, event=event,
        validation=validate(generated, bundle['request'], mode=mode))
    save(ROOT/'results'/(event['id']+'.json'), result)
    print(dict(condition=item['condition'], mode=mode, validation=result['validation']), flush=True)
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    save(ROOT/'started.json', dict(job=os.environ['SLURM_JOB_ID']))
    with (ROOT/'model_service.log').open('x') as log:
        process = subprocess.Popen(['bash', str(ROOT/'model_environment.sh')], stdout=log, stderr=subprocess.STDOUT)
        with patch.object(nc_controller, 'ROOT', ROOT):
            try:
                nc_controller.ready(process)
                rows = [generate(item, mode) for item in manifest['inputs'] for mode in ('direct', 'diagnostic')]
            finally:
                clean = nc_controller.stop(process)
    assert clean and read(ROOT/'service/stopped.json')['calls'] == 4
    verify()
    save(ROOT/'complete.json', dict(model_calls=4, physical_attempts=0, training_ready=False,
        valid=sum(r['validation']['valid'] for r in rows), causal_correctness_not_established=True))


if __name__ == '__main__':
    main()
