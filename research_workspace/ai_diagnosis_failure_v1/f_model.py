"""门禁后仅两次离线请求；独占标记防重跑，不运行仿真或执行提议。"""
import os
import unittest
from f_common import ROOT, PARENT, read, save, sha, verify
from f_response import MODES, SEED, MAX_TOKENS, validate

FILES = ('f_response.py', 'test_f_response.py', 'f_generator.py', 'f_model.py',
         'f_model_audit.py', 'model.sbatch', 'model_audit.sbatch')


def freeze():
    verify()
    audit = read(ROOT/'verification.json')
    assert audit['passed'] and audit['model_smoke_gate'] and audit['natural_failure_samples'] == 0
    for path, digest in audit['identities'].items():
        assert sha(path) == digest, path
    bundle = read(ROOT/'run/model_input_0.json')
    assert bundle['direct_messages'][1] == bundle['diagnostic_messages'][1]
    request = bundle['request']
    assert request['budget']['observations_remaining'] == 2
    frames = next(r['value'] for r in request['evidence'] if r['field'] == 'rgbd_surface_observations')
    assert len(frames) == 1 and frames[0]['observation_index'] == 0
    tests = unittest.TestLoader().discover(str(ROOT), pattern='test_f_response.py')
    result = unittest.TextTestRunner(verbosity=2).run(tests)
    assert result.wasSuccessful()
    paths = [ROOT/name for name in FILES]+[ROOT/'verification.json', ROOT/'run/model_input_0.json',
                                          PARENT/'candidate_sft_v2/manifest.json']
    save(ROOT/'model_manifest.json', dict(modes=list(MODES), max_calls=2, seed=SEED, max_tokens=MAX_TOKENS,
         temperature=0, enable_thinking=False, adapter_enabled=False, physical_execution_authorized=False,
         snapshot_observation_index=0, tests=result.testsRun, identities={str(p): sha(p) for p in paths}))
    return bundle


def call(generator, bundle, *, mode):
    messages = bundle[mode+'_messages']
    values = generator.prepare(messages)
    request = dict(mode=mode, messages=messages, temperature=0, seed=SEED, max_tokens=MAX_TOKENS,
                   chat_template_kwargs={'enable_thinking': False}, physical_execution_authorized=False)
    save(ROOT/'model'/f'{mode}_request.json', request)
    save(ROOT/'model'/f'{mode}_started.json', dict(job=os.environ['SLURM_JOB_ID'], invocation=1))
    try:
        response = generator.generate(values)
    except Exception as error:
        save(ROOT/'model'/f'{mode}_error.json', dict(type=type(error).__name__, message=str(error)))
        return dict(mode=mode, calls=1, valid=False, status='generation_error')
    save(ROOT/'model'/f'{mode}_response.json', response)
    checked = validate(response, bundle['request'], mode=mode)
    save(ROOT/'model'/f'{mode}_validation.json', checked)
    return dict(mode=mode, calls=1, valid=checked['valid'], status='generated',
                finish_reason=response['finish_reason'], completion_tokens=response['completion_tokens'])


def main():
    assert os.environ.get('SLURM_JOB_ID')
    bundle = freeze()
    from f_generator import Generator
    generator = Generator()
    save(ROOT/'model/environment.json', dict(environment=generator.environment, identity=generator.identity))
    rows = [call(generator, bundle, mode=mode) for mode in MODES]
    manifest = read(ROOT/'model_manifest.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    save(ROOT/'model_complete.json', dict(rows=rows, actual_calls=sum(r['calls'] for r in rows),
         physical_executions=0, training_runs=0, model_manifest_sha256=sha(ROOT/'model_manifest.json')))
    print(rows, flush=True)


if __name__ == '__main__':
    main()
