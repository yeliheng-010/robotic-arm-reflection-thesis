"""Loopback-only frozen local teacher; never uses the smoke adapter or a paid API."""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model', required=True)
    p.add_argument('--port', type=int, default=18765)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    if torch.cuda.device_count() != 1:
        raise RuntimeError('Requires exactly one Slurm-assigned GPU')
    torch.set_num_threads(4)
    torch.backends.cuda.enable_flash_sdp(False)
    tokenizer = AutoTokenizer.from_pretrained(a.model, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        a.model, local_files_only=True, torch_dtype=torch.float16,
        device_map={'': 0}, attn_implementation='sdpa',
        quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type='nf4',
            bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.float16))
    model.eval()
    info = {'model': a.model, 'adapter': None, 'frozen': True, 'port': a.port,
            'prompt_format': 'text-reflection-v2', 'started': time.time()}

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value):
            data = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self.reply(200, info) if self.path == '/health' else self.reply(404, {})

        def do_POST(self):
            if self.path != '/reflect':
                self.reply(404, {})
                return
            try:
                n = int(self.headers.get('Content-Length', 0))
                if not 0 < n <= 100000:
                    raise ValueError('Invalid request size')
                request = json.loads(self.rfile.read(n))
                messages = request['messages']
                if [m['role'] for m in messages] != ['system', 'user']:
                    raise ValueError('Expected system and user messages')
                text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                inputs = tokenizer(text, add_special_tokens=False, return_tensors='pt').to('cuda')
                if inputs.input_ids.shape[1] > 4096:
                    raise ValueError('Prompt exceeds 4096 tokens')
                started = time.monotonic()
                with torch.inference_mode():
                    out = model.generate(**inputs, max_new_tokens=256, do_sample=False,
                        pad_token_id=tokenizer.eos_token_id)
                answer = tokenizer.decode(out[0, inputs.input_ids.shape[1]:], skip_special_tokens=True)
                result = {'text': answer, 'teacher': info, 'elapsed_s': time.monotonic()-started,
                          'input_tokens': int(inputs.input_ids.shape[1]),
                          'output_tokens': int(out.shape[1]-inputs.input_ids.shape[1])}
                event = {'request': request, 'response': result, 'time': time.time()}
                with (a.output/'requests.jsonl').open('a') as f:
                    f.write(json.dumps(event, ensure_ascii=False)+'\n')
                self.reply(200, result)
            except Exception as e:
                self.reply(422, {'error': type(e).__name__, 'message': str(e)})

        def log_message(self, *_):
            pass

    server = HTTPServer(('127.0.0.1', a.port), Handler)
    (a.output/'ready.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info), flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
