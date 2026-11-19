"""只加载基础4B，所有生成显式关闭adapter，启动回放固定旧开发输入。"""
import time
import uuid
import torch
from runtime import verify_manifest,setup
from om_stopping import finish_reason
from rc_common import ROOT,PARENT,ALIAS,read,save,identity
from rc_client import MAX_TOKENS,payload,check_response

MAX_INPUT_TOKENS=16384


class Generator:
    def __init__(self):
        self.model,_,self.tok,self.environment=setup(verify_manifest())
        self.model.eval()

    def prepare(self,body):
        assert set(body)=={'model','messages','temperature','seed','max_tokens','chat_template_kwargs'}
        assert body['model']==ALIAS and body['temperature']==0 and body['seed']==42
        assert body['max_tokens']==MAX_TOKENS and body['chat_template_kwargs']=={'enable_thinking':False}
        assert [m['role'] for m in body['messages']]==['system','user']
        prompt=self.tok.apply_chat_template(body['messages'],tokenize=False,
            add_generation_prompt=True,enable_thinking=False)
        ids=self.tok(prompt,add_special_tokens=False,return_tensors='pt').to('cuda')
        assert ids['input_ids'].shape[1]<=MAX_INPUT_TOKENS,'Long input rejected without truncation'
        return ids

    def generate(self,body):
        ids=self.prepare(body)
        length=ids['input_ids'].shape[1]
        started=time.monotonic()
        with self.model.disable_adapter(),torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            output=self.model.generate(**ids,max_new_tokens=MAX_TOKENS,do_sample=False,
                use_cache=True,logits_to_keep=1,pad_token_id=self.tok.pad_token_id)
        generated=output[0,length:]
        eos=self.model.generation_config.eos_token_id
        reason=finish_reason(int(generated[-1]),eos_ids=eos,generated=len(generated),budget=MAX_TOKENS)
        response=dict(id=uuid.uuid4().hex,model=ALIAS,identity=identity(),
            active_method='base',active_adapter_sha256=None,
            choices=[dict(finish_reason=reason,message=dict(role='assistant',
                content=self.tok.decode(generated,skip_special_tokens=True)))],
            usage=dict(prompt_tokens=length,completion_tokens=len(generated)),
            stopping=dict(last_token=int(generated[-1]),eos_ids=eos,generated_ids=generated.tolist()),
            elapsed_s=time.monotonic()-started)
        save(ROOT/'service/requests'/f"{response['id']}.json",dict(request=body,response=response))
        return response


def replay(generator):
    directory=PARENT/'set_sft_v1'
    raw=read(directory/'eval.json')
    expected={}
    for shard in range(3):
        for row in read(directory/'evaluation/before'/f'shard_{shard}/result.json')['rows']:
            if row['method']=='base':
                expected[row['index']]=row['text']
    checks=[]
    for index in (0,52):
        assert raw[index]['split']=='dev'
        response=generator.generate(payload(raw[index]['messages']))
        assert check_response(response)==expected[index],'Base replay changed'
        checks.append(dict(index=index,request_id=response['id']))
    return checks
