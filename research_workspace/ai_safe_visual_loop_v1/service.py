import os
from pathlib import Path
from http.server import HTTPServer
from unittest.mock import patch
import nc_service
from mm_generator import VisualGenerator
from vs_transport import execute
from sv_common import ROOT, PORT, save, sha, verify


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = verify()
    with patch.object(nc_service, 'execute', execute), HTTPServer(('127.0.0.1', PORT), nc_service.Handler) as server:
        server.root, server.timeout, server.calls = ROOT, 1., 0
        server.max_calls, server.max_decisions = manifest['max_model_calls'], 4
        server.conditions = {c['item']['id'] for c in manifest['cases']}
        server.image_roots = [(ROOT/'cases').resolve()]
        server.generator = VisualGenerator()
        save(ROOT/'service/ready.json', dict(manifest_sha256=sha(ROOT/'manifest.json'),
            environment=server.generator.environment, identity=server.generator.identity, startup_generations=0))
        while not (ROOT/'stop_service.json').exists():
            server.handle_request()
        save(ROOT/'service/stopped.json', dict(calls=server.calls, stopped=True))


if __name__ == '__main__':
    main()
