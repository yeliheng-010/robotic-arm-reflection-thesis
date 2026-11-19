"""同一基础4B加载两个adapter，切换与保存参考logits逐项核验。"""
import time
import uuid
import torch
from om_common import ROOT, SFT, NEW_SFT, ALIASES, read, save, model_identity, requested_adapter
from runtime import verify_manifest, setup
from smoke import probe
from om_adapter_route import activate
from om_stopping import finish_reason

MAX_INPUT_TOKENS = 16384
MAX_NEW_TOKENS = 128
RELOAD_TOLERANCE = 1e-4


class Generator:
    def __init__(self):
        config = verify_manifest()
        self.model, _, self.tok, self.environment = setup(config)
        for method, directory in (('previous159', SFT), ('new189', NEW_SFT)):
            self.model.load_adapter(str(directory/'training/adapter'),
                                    adapter_name=method, is_trainable=False)
        self.model.set_adapter('previous159')
        self.model.eval()
        self.reload_errors = self.check_reload()

    def check_reload(self):
        errors = {}
        rows = {'previous159': read(SFT/'dev_encoded.json')[0],
                'new189': read(NEW_SFT/'eval_encoded.json')[0]['variants'][0]}
        roots = {'previous159': SFT, 'new189': NEW_SFT}
        for method in ('new189', 'previous159', 'new189', 'previous159'):
            expected = torch.load(roots[method]/'training/reference_logits.pt', weights_only=True)
            with activate(self.model, method):
                actual = probe(self.model, rows[method])
            error = float((expected-actual).abs().max())
            assert error <= RELOAD_TOLERANCE, (method, error)
            errors[method] = max(errors.get(method, 0), error)
        return errors

    def prepare(self, body):
        assert set(body) == {'model','messages','temperature','seed','max_tokens','chat_template_kwargs'}
        assert body['model'] in ALIASES.values() and body['temperature'] == 0 and body['seed'] == 42
        assert body['max_tokens'] == MAX_NEW_TOKENS and body['chat_template_kwargs'] == {'enable_thinking':False}
        assert [m['role'] for m in body['messages']] == ['system', 'user']
        prompt = self.tok.apply_chat_template(body['messages'], tokenize=False,
                                             add_generation_prompt=True, enable_thinking=False)
        ids = self.tok(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
        assert ids['input_ids'].shape[1] <= MAX_INPUT_TOKENS, 'Long input rejected without truncation'
        method = next(m for m, alias in ALIASES.items() if alias == body['model'])
        return method, ids

    def generate(self, body):
        method, ids = self.prepare(body)
        length = ids['input_ids'].shape[1]
        started = time.monotonic()
        with activate(self.model, method), torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            output = self.model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False,
                use_cache=True, logits_to_keep=1, pad_token_id=self.tok.pad_token_id)
        generated = output[0, length:]
        eos = self.model.generation_config.eos_token_id
        reason = finish_reason(int(generated[-1]), eos_ids=eos,
                               generated=len(generated), budget=MAX_NEW_TOKENS)
        response = dict(id=uuid.uuid4().hex, model=body['model'], identity=model_identity(),
            active_method=method, active_adapter_sha256=requested_adapter(method),
            choices=[dict(finish_reason=reason, message=dict(role='assistant',
                          content=self.tok.decode(generated, skip_special_tokens=True)))],
            usage=dict(prompt_tokens=length, completion_tokens=len(generated)),
            stopping=dict(last_token=int(generated[-1]), eos_ids=eos, generated_ids=generated.tolist()),
            elapsed_s=time.monotonic()-started)
        save(ROOT/'service/requests'/f"{response['id']}.json", dict(request=body, response=response))
        return response


def replay(generator):
    from om_client import payload_for, check_response
    raw = read(NEW_SFT/'eval.json')
    expected = {}
    for mode in ('before', 'after'):
        for shard in range(3):
            for row in read(NEW_SFT/'evaluation'/mode/f'shard_{shard}/result.json')['rows']:
                expected[(row['method'], row['index'])] = row['text']
    # 同一个开发输入交替切换两轮，再回放原基础模型发生分歧的开发输入。
    checks = []
    for index in (0, 0, 52):
        assert raw[index]['split'] == 'dev'
        for method in ('new189', 'base', 'previous159'):
            response = generator.generate(payload_for(method, raw[index]['messages']))
            assert check_response(response, method) == expected[(method, index)], 'Offline replay changed'
            checks.append(dict(method=method, index=index, request_id=response['id']))
    return checks
