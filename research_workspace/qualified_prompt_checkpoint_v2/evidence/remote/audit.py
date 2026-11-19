"""独立重建实际编码并检查原始响应；不加载模型权重或调用generate。"""
import hashlib
import json
import os
import numpy as np
from transformers import AutoProcessor
from qualified_prompt_checkpoint_v2.common import ROOT, RUN, read, save, sha, verify


def request_check(manifest):
    before = read(manifest['baseline_request'])
    actual = read(RUN / 'request.json')
    body = json.loads(actual['messages'][1]['content'])
    original = json.loads(before['messages'][1]['content'])
    checkpoint = body.pop('decision_checkpoint')
    draft = json.loads(read(ROOT / 'B_checkpoint.json')['request']['messages'][1]['content'])
    assert checkpoint == draft['decision_checkpoint']
    assert checkpoint['latest_public_rejection'] == original['history'][-1]
    assert body['budget'] == dict(decisions=1, planning=0, observations=0)
    body['budget'] = original['budget']
    assert body == original
    restored = dict(actual)
    restored['messages'] = [dict(row) for row in actual['messages']]
    restored['messages'][1]['content'] = before['messages'][1]['content']
    assert restored == before
    return actual, original['history']


def tensor_check(request):
    saved = read(RUN / 'encoding.json')
    assert saved['npz_sha256'] == sha(RUN / 'input_tensors.npz')
    processor = AutoProcessor.from_pretrained(saved['identity']['model_path'], local_files_only=True,
        trust_remote_code=False, min_pixels=128 * 128, max_pixels=448 * 448)
    multimodal = [request['messages'][0], dict(role='user', content=[
        dict(type='image', image=request['image']), dict(type='text', text=request['messages'][1]['content'])])]
    tensors = processor.apply_chat_template(multimodal, tokenize=True, return_dict=True,
        return_tensors='pt', add_generation_prompt=True, enable_thinking=False)
    with np.load(RUN / 'input_tensors.npz', allow_pickle=False) as archived:
        assert set(archived.files) == set(tensors)
        for key, tensor in tensors.items():
            value = tensor.detach().cpu().numpy()
            assert np.array_equal(archived[key], value), key
            assert saved['tensors'][key] == dict(shape=list(value.shape), dtype=str(value.dtype),
                sha256=hashlib.sha256(value.tobytes()).hexdigest())
        assert saved['input_ids'] == archived['input_ids'].tolist()
        assert saved['attention_mask'] == archived['attention_mask'].tolist()
    templates = read(RUN / 'templates.json')
    assert templates['processor_chat_template'] == processor.chat_template
    assert templates['tokenizer_chat_template'] == processor.tokenizer.chat_template
    assert templates['decoded_input'] == processor.tokenizer.decode(saved['input_ids'][0], skip_special_tokens=False)
    assert saved['encoding']['input_tokens'] == len(saved['input_ids'][0]) <= 16384
    return processor.tokenizer, saved


def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate_key')
        value[key] = item
    return value


def independent_response(response, history, *, request):
    body = json.loads(request['messages'][1]['content'])
    try:
        assert response['finish_reason'] == 'stop'
        assert isinstance(response['text'], str) and len(response['text']) <= 4096
        value = json.loads(response['text'], object_pairs_hook=unique)
        assert isinstance(value, dict) and set(value) == {'action'}
        action = value['action']
        assert isinstance(action, dict) and set(action) == {'id', 'args'}
        assert action['id'] in ('PROPOSE_GRASP', 'STOP') and isinstance(action['args'], dict)
        if action['id'] == 'STOP':
            assert action['args'] == {}
            return dict(valid=True, action=action, status='model_stopped')
        choices = body['actions'][0]['allowed_values']
        assert set(action['args']) == set(choices)
        for key, options in choices.items():
            assert type(action['args'][key]) is (str if key == 'region' else int)
            assert action['args'][key] in options
        assert action['args']['tilt_deg'] != 0 or action['args']['azimuth_deg'] == 0
        repeat = any(row['action'] == action for row in history)
        return dict(valid=True, action=action, status='repeated_rejected_action' if repeat else 'novel_action_unchecked')
    except (AssertionError, ValueError, TypeError, KeyError):
        return dict(valid=False, action=None, status='invalid')


def budget_and_response(tokenizer, saved, *, request, history):
    claim = read(RUN / 'model_claim.json')
    assert claim == dict(ordinal=1, consumed=1, request_sha256=sha(RUN / 'request.json'))
    assert read(RUN / 'generation_started.json')['input_tensors_sha256'] == saved['npz_sha256']
    response = read(RUN / 'response.json')
    assert response['prompt_tokens'] == saved['encoding']['input_tokens']
    assert response['identity'] == saved['identity'] and response['identity']['adapter_enabled'] is False
    assert response['completion_tokens'] == len(response['generated_ids'])
    assert response['text'] == tokenizer.decode(response['generated_ids'], skip_special_tokens=True)
    eos = response['eos_ids'] if isinstance(response['eos_ids'], list) else [response['eos_ids']]
    expected_finish = 'stop' if response['generated_ids'][-1] in eos else 'length'
    assert expected_finish == response['finish_reason']
    if expected_finish == 'length':
        assert len(response['generated_ids']) == 2048
    result = read(RUN / 'result.json')
    checked = independent_response(response, history, request=request)
    assert checked == {key: result[key] for key in ('valid', 'action', 'status')}
    for key, expected in dict(model_calls=1, planning=0, physical=0, training=0, retries=0,
                              safety_evaluated=False, ready=False).items():
        assert result[key] == expected
    assert not any((RUN / name).exists() for name in ('proposal.json', 'private_plan.json', 'physical', 'execution_manifest.json'))
    return checked


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    request, history = request_check(manifest)
    tokenizer, saved = tensor_check(request)
    checked = budget_and_response(tokenizer, saved, request=request, history=history)
    config = read(RUN / 'generation_config.json')
    assert config['explicit'] == dict(max_new_tokens=2048, do_sample=False, use_cache=True,
                                     logits_to_keep=1, pad_token_id=tokenizer.pad_token_id)
    assert config['seed'] == 42 and config['enable_thinking'] is False
    for name, expected in config['loaded_project_sources'].items():
        assert manifest['identities'][name] == expected == sha(name)
    save(RUN / 'audit_result.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'],
         checked=checked, input_tokens=saved['encoding']['input_tokens'],
         tensor_keys=sorted(saved['tensors']), full_tensor_reencoding_equal=True,
         frozen_identities=len(manifest['identities']), model_calls_added=0))
    print(dict(passed=True, status=checked['status'], full_tensor_reencoding_equal=True), flush=True)


if __name__ == '__main__':
    main()
