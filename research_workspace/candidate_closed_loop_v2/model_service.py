"""本轮独占的串行4B推理服务；基础/微调仅切换adapter。"""
import json
import time
import uuid
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler,HTTPServer
import torch
from common import ROOT,SFT,PORT,ALIASES,read,save,sha,verify,model_identity
from runtime import verify_manifest,setup
from smoke import probe
from stopping import finish_reason

MAX_INPUT_TOKENS=16384


class Generator:
    def __init__(self):
        config=verify_manifest()
        self.model,_,self.tok,self.environment=setup(config,adapter=SFT/'training/adapter')
        self.model.eval()
        expected=torch.load(SFT/'training/reference_logits.pt',weights_only=True)
        actual=probe(self.model,read(SFT/'dev_encoded.json')[0])
        self.reload_error=float((expected-actual).abs().max())
        assert self.reload_error<=1e-4

    def generate(self,body):
        assert set(body)=={'model','messages','temperature','seed','max_tokens','chat_template_kwargs'}
        assert body['model'] in ALIASES.values() and body['temperature']==0 and body['seed']==42
        assert body['max_tokens']==128 and body['chat_template_kwargs']=={'enable_thinking':False}
        assert [m['role'] for m in body['messages']]==['system','user']
        prompt=self.tok.apply_chat_template(body['messages'],tokenize=False,add_generation_prompt=True,
                                             enable_thinking=False)
        ids=self.tok(prompt,add_special_tokens=False,return_tensors='pt').to('cuda')
        length=ids['input_ids'].shape[1]
        assert length<=MAX_INPUT_TOKENS,'Long input rejected without truncation'
        context=self.model.disable_adapter() if body['model']==ALIASES['base'] else nullcontext()
        started=time.monotonic()
        with context,torch.inference_mode(),torch.autocast('cuda',dtype=torch.float16):
            output=self.model.generate(**ids,max_new_tokens=128,do_sample=False,use_cache=True,
                                      logits_to_keep=1,pad_token_id=self.tok.pad_token_id)
        generated=output[0,length:]
        reason=finish_reason(int(generated[-1]),eos_ids=self.model.generation_config.eos_token_id,
                             generated=len(generated),budget=128)
        response=dict(id=uuid.uuid4().hex,model=body['model'],identity=model_identity(),
            choices=[dict(finish_reason=reason,
                          message=dict(role='assistant',content=self.tok.decode(generated,skip_special_tokens=True)))],
            usage=dict(prompt_tokens=length,completion_tokens=len(generated)),
            stopping=dict(last_token=int(generated[-1]),eos_ids=self.model.generation_config.eos_token_id),
            elapsed_s=time.monotonic()-started)
        save(ROOT/'service/requests'/f"{response['id']}.json",dict(request=body,response=response))
        return response


def replay(generator):
    from client import payload_for,check_response
    rows=[json.loads(line) for line in (SFT.parent/'data_review_v1/output_v1/dev_combined.jsonl').read_text().splitlines()]
    results={}
    for method,mode in (('base','before'),('tuned','after')):
        saved=read(SFT/'evaluation'/mode/'shard_0/result.json')['rows']
        expected=next(r for r in saved if r['split']=='dev' and r['index']==0)['text']
        response=generator.generate(payload_for(method,rows[0]['messages'][:-1]))
        assert check_response(response,method)==expected,'Frozen offline replay mismatch'
        results[method]=response['id']
    return results


def serve():
    verify()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass

        def respond(self,status,body):
            data=json.dumps(body,ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.respond(200 if self.path=='/health' else 404,health)

        def do_POST(self):
            try:
                assert self.path=='/v1/chat/completions'
                size=int(self.headers['Content-Length'])
                assert 0<size<2_000_000
                body=json.loads(self.rfile.read(size))
                self.respond(200,generator.generate(body))
            except Exception as error:
                save(ROOT/'service'/f'error_{uuid.uuid4().hex}.json',dict(error=repr(error)))
                self.respond(500,dict(error=repr(error)))
    server=HTTPServer(('127.0.0.1',PORT),Handler)
    server.timeout=2
    generator=Generator()
    checks=replay(generator)
    health=dict(status='ready',models=list(ALIASES.values()),identity=model_identity(),
                reload_error=generator.reload_error,replay=checks,environment=generator.environment)
    save(ROOT/'service/ready.json',health)
    try:
        while not (ROOT/'stop_service.json').exists():
            server.handle_request()
    finally:
        server.server_close()
        save(ROOT/'service/stopped.json',dict(stopped=True,at=time.time()))


if __name__=='__main__':
    serve()
