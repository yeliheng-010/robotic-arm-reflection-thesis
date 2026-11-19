"""仅监听 loopback 的冻结教师；所有请求与真实输出保留。"""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import time

from training.refine.runtime import FrozenModel

MAX_REQUEST_BYTES = 100000


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {'messages'}:
        raise ValueError('Expected messages object')
    messages = request['messages']
    if not isinstance(messages, list) or len(messages) != 2:
        raise ValueError('Expected system and user messages')
    for message, role in zip(messages, ('system', 'user')):
        if not isinstance(message, dict) or message.get('role') != role:
            raise ValueError('Expected system and user messages')
        if not isinstance(message.get('content'), str) or not message['content'].strip():
            raise ValueError('Expected nonempty text content')
    return messages


def handler_class(model, output):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            info = dict(model=model.path, architecture=model.architecture, adapter=None,
                        frozen=True, max_new_tokens=model.max_new_tokens, thinking=model.thinking)
            self.reply(200, info) if self.path == '/health' else self.reply(404, {})

        def do_POST(self):
            if self.path != '/reflect':
                self.reply(404, {})
                return
            event = dict(time=time.time())
            try:
                length = int(self.headers.get('Content-Length', 0))
                if not 0 < length <= MAX_REQUEST_BYTES:
                    raise ValueError('Invalid request size')
                event['request'] = json.loads(self.rfile.read(length))
                messages = validate_request(event['request'])
                started = time.monotonic()
                event['response'] = model.generate(messages)
                event['elapsed_s'] = time.monotonic() - started
                self.reply(200, event['response'])
            except Exception as error:
                event['error'] = str(error)
                self.reply(422, {'error': str(error)})
            finally:
                with (output / 'requests.jsonl').open('a') as stream:
                    stream.write(json.dumps(event, ensure_ascii=False) + '\n')

        def log_message(self, *_):
            pass
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--architecture', choices=['qwen25', 'qwen35'], required=True)
    parser.add_argument('--port', type=int, default=18821)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--thinking', action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    model = FrozenModel(args.architecture, thinking=args.thinking)
    with HTTPServer(('127.0.0.1', args.port), handler_class(model, args.output)) as server:
        print(json.dumps({'ready': True, 'model': model.path, 'port': args.port}), flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()

