"""重读原始请求和完整输出核验；无新生成，不评价解释为真实因果。"""
import os
from f_common import ROOT, read, save, sha, verify
from f_response import MODES, SEED, MAX_TOKENS, finish, validate


def audit_mode(mode, bundle):
    folder = ROOT/'model'
    request = read(folder/f'{mode}_request.json')
    assert request['messages'] == bundle[mode+'_messages']
    assert request['max_tokens'] == MAX_TOKENS and request['seed'] == SEED
    assert request['temperature'] == 0 and request['physical_execution_authorized'] is False
    assert request['chat_template_kwargs'] == {'enable_thinking': False}
    assert read(folder/f'{mode}_started.json')['invocation'] == 1
    if (folder/f'{mode}_error.json').exists():
        return dict(mode=mode, calls=1, valid=False, error=read(folder/f'{mode}_error.json'))
    response = read(folder/f'{mode}_response.json')
    assert len(response['generated_ids']) == response['completion_tokens'] <= MAX_TOKENS
    assert finish(response['generated_ids'], response['eos_ids']) == response['finish_reason']
    assert response['identity']['adapter_enabled'] is False
    checked = validate(response, bundle['request'], mode=mode)
    assert checked == read(folder/f'{mode}_validation.json')
    return dict(mode=mode, calls=1, valid=checked['valid'], parsed=checked['parsed'], error=checked['error'],
                finish_reason=response['finish_reason'], prompt_tokens=response['prompt_tokens'],
                completion_tokens=response['completion_tokens'], elapsed_s=response['elapsed_s'])


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify()
    manifest, complete = read(ROOT/'model_manifest.json'), read(ROOT/'model_complete.json')
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    assert complete['model_manifest_sha256'] == sha(ROOT/'model_manifest.json')
    bundle = read(ROOT/'run/model_input_0.json')
    rows = [audit_mode(mode, bundle) for mode in MODES]
    assert complete['actual_calls'] == len(list((ROOT/'model').glob('*_started.json'))) == 2
    assert complete['physical_executions'] == complete['training_runs'] == 0
    direct, diagnostic = (read(ROOT/'model'/f'{mode}_request.json') for mode in MODES)
    assert direct['messages'][1] == diagnostic['messages'][1]
    paths = [p for p in (ROOT/'model').iterdir() if p.is_file()]
    value = dict(passed=True, rows=rows, calls=2, valid_proposals=sum(r['valid'] for r in rows),
         same_visible_input=True, future_observations_excluded=True, proposal_executions=0, training_runs=0,
         natural_failure_samples=0, cause_correctness_validated=False,
         model_manifest_sha256=sha(ROOT/'model_manifest.json'), identities={str(p): sha(p) for p in paths})
    save(ROOT/'model_verification.json', value)
    print({k: v for k, v in value.items() if k != 'identities'}, flush=True)


if __name__ == '__main__':
    main()
