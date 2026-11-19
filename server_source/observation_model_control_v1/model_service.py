"""本轮独占串行HTTP服务，所有请求只使用可见反馈。"""
import json
import time
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from om_common import ROOT, PORT, ALIASES, save, verify, model_identity
from om_generator import Generator, replay

MAX_REQUEST_BYTES = 2_000_000
SERVER_POLL_SECONDS = 2


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, status, body):
        data = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.respond(200 if self.path == '/health' else 404, self.server.health)

    def do_POST(self):
        try:
            assert self.path == '/v1/chat/completions'
            size = int(self.headers['Content-Length'])
            assert 0 < size < MAX_REQUEST_BYTES
            body = json.loads(self.rfile.read(size))
            self.respond(200, self.server.generator.generate(body))
        except Exception as error:
            save(ROOT/'service'/f'error_{uuid.uuid4().hex}.json', dict(error=repr(error)))
            self.respond(500, dict(error=repr(error)))


def serve():
    verify()
    with HTTPServer(('127.0.0.1', PORT), Handler) as server:
        server.timeout = SERVER_POLL_SECONDS
        server.generator = Generator()
        checks = replay(server.generator)
        server.health = dict(status='ready', models=list(ALIASES.values()), identity=model_identity(),
            reload_errors=server.generator.reload_errors, replay_passed=True, replay=checks,
            environment=server.generator.environment)
        save(ROOT/'service/ready.json', server.health)
        while not (ROOT/'stop_service.json').exists():
            server.handle_request()
    save(ROOT/'service/stopped.json', dict(stopped=True, at=time.time()))


if __name__ == '__main__':
    try:
        serve()
    except BaseException as error:
        save(ROOT/'service/failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
