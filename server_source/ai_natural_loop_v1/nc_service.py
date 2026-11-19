"""单卡串行服务；固定逐轨迹请求上限，无健康回放生成。"""
import json
import re
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from f_generator import Generator
from nc_common import ROOT, PORT, MAX_DECISIONS, read, save, sha, verify, status

MAX_BYTES = 300000


def execute(server, body):
    assert set(body) == {'condition', 'mode', 'ordinal', 'request', 'messages'}
    assert body['condition'] in server.conditions and body['mode'] in ('direct', 'diagnostic')
    assert type(body['ordinal']) is int and 1 <= body['ordinal'] <= MAX_DECISIONS
    key = f"{body['condition']}_{body['mode']}_{body['ordinal']}"
    assert re.fullmatch(r'[A-Za-z0-9_]+', key)
    assert server.calls < server.max_calls
    save(ROOT/'service/requests'/f'{key}_request.json', body)
    server.calls += 1
    started = time.monotonic()
    try:
        response = server.generator.generate(server.generator.prepare(body['messages']))
    except Exception as error:
        save(ROOT/'service/requests'/f'{key}_error.json', dict(error=repr(error), calls=1))
        raise
    event = dict(id=key, response=response, manifest_sha256=sha(ROOT/'manifest.json'),
                 elapsed_s=time.monotonic()-started)
    save(ROOT/'service/requests'/f'{key}_response.json', event)
    status(ROOT/'service/status.json', dict(calls=server.calls, latest=key))
    return event


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, code, value):
        data = json.dumps(value, ensure_ascii=False, allow_nan=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            assert self.path == '/generate'
            size = int(self.headers['Content-Length'])
            assert 0 < size <= MAX_BYTES
            self.respond(200, execute(self.server, json.loads(self.rfile.read(size))))
        except Exception as error:
            self.respond(500, dict(error=repr(error)))


def main():
    manifest = verify()
    with HTTPServer(('127.0.0.1', PORT), Handler) as server:
        server.timeout, server.calls = 1., 0
        server.conditions = {r['item']['id'] for r in manifest['cases']}
        server.max_calls = manifest['max_model_calls']
        server.generator = Generator()
        save(ROOT/'service/ready.json', dict(manifest_sha256=sha(ROOT/'manifest.json'),
             environment=server.generator.environment, identity=server.generator.identity, startup_generations=0))
        while not (ROOT/'stop_service.json').exists():
            server.handle_request()
        save(ROOT/'service/stopped.json', dict(calls=server.calls, stopped=True))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'service/failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
