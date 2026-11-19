"""续跑仅开放未消费条件；模型请求沿用原账本，生命周期另存。"""
import os
from http.server import HTTPServer
from unittest.mock import patch
import nc_service
from mm_generator import VisualGenerator
from vs_transport import execute
from sv_common import ROOT, PORT, read, save, sha, verify

LIFECYCLE = ROOT/'resume_v5'


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest, resume = verify(), read(LIFECYCLE/'manifest.json')
    assert all(sha(p) == h for p, h in resume['identities'].items())
    with patch.object(nc_service, 'execute', execute), HTTPServer(('127.0.0.1', PORT), nc_service.Handler) as server:
        server.root, server.timeout = ROOT, 1.
        server.calls = len(list((ROOT/'service/requests').glob('*_request.json')))
        assert server.calls == resume['previous_model_calls']
        server.max_calls, server.max_decisions = manifest['max_model_calls'], 4
        server.conditions = set(resume['pending'])
        server.image_roots = [(ROOT/'cases').resolve()]
        server.generator = VisualGenerator()
        assert server.generator.identity == read(ROOT/'service/ready.json')['identity']
        save(LIFECYCLE/'service/ready.json', dict(identity=server.generator.identity,
            environment=server.generator.environment, startup_generations=0, previous_calls=server.calls))
        while not (LIFECYCLE/'stop_service.json').exists():
            server.handle_request()
        save(LIFECYCLE/'service/stopped.json', dict(calls=server.calls, stopped=True))


if __name__ == '__main__':
    main()
