"""单进程串行推理，基础模型禁用全部adapter，微调组启用冻结pilot。"""
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import time
import torch
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.loop_freeze import ROOT, verify
from stability.loop_protocol import PORT, MAX_NEW_TOKENS, validate_call
from stability.sft_model import device_setup, load_model, tokenizer


class Inference:
    def __init__(self):
        self.frozen = verify()
        self.environment = device_setup(42)
        config = json.loads((OUT/'pilot_sft_v1/manifest.json').read_text())
        self.tokenizer = tokenizer(config['model'])
        self.model, _ = load_model(config)
        self.model.load_adapter(self.frozen['adapter'], adapter_name='pilot', is_trainable=False)
        self.model.set_adapter('pilot')
        self.model.eval()
        self.model.requires_grad_(False)

    @torch.no_grad()
    def generate(self, request):
        arm, messages = validate_call(request)
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False,
            add_generation_prompt=True, enable_thinking=False)
        inputs = self.tokenizer(prompt, add_special_tokens=False, return_tensors='pt').to('cuda')
        assert inputs['input_ids'].shape[1] <= 4096, 'Prompt too long; no truncation'
        context = self.model.disable_adapter() if arm == 'base' else nullcontext()
        started = time.monotonic()
        with context, torch.autocast('cuda', dtype=torch.float16):
            tokens = self.model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS,
                do_sample=False, use_cache=True, pad_token_id=self.tokenizer.eos_token_id)
        text = self.tokenizer.decode(tokens[0, inputs['input_ids'].shape[1]:], skip_special_tokens=True)
        return dict(arm=arm, text=text, input_tokens=inputs['input_ids'].shape[1],
            output_tokens=tokens.shape[1]-inputs['input_ids'].shape[1], elapsed_s=time.monotonic()-started,
            adapter=self.frozen['adapter'] if arm == 'adapted' else None)


def handler(model):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            self.reply(200, {'ready': True, 'environment': model.environment})

        def do_POST(self):
            event = {'time': time.time()}
            try:
                assert self.path == '/reflect'
                length = int(self.headers.get('Content-Length', 0))
                assert 0 < length <= 100000
                event['request'] = json.loads(self.rfile.read(length))
                event['response'] = model.generate(event['request'])
                self.reply(200, event['response'])
            except Exception as error:
                event['error'] = repr(error)
                self.reply(422, {'error': repr(error)})
            finally:
                with (ROOT/'service_requests.jsonl').open('a') as stream:
                    stream.write(json.dumps(event, ensure_ascii=False)+'\n')

        def log_message(self, *_):
            pass
    return Handler


def main():
    model = Inference()
    atomic(ROOT/'service_ready.json', {'environment': model.environment, 'port': PORT})
    with HTTPServer(('127.0.0.1', PORT), handler(model)) as server:
        server.serve_forever()


if __name__ == '__main__':
    main()
