import runpy
from reflection.__main__ import bootstrap
bootstrap()
from sv_common import ROOT
from sv_requests_v2 import context as request_context
from sv_span_audit import context as span_context


if __name__ == '__main__':
    with request_context(), span_context():
        runpy.run_path(str(ROOT/'audit.py'), run_name='__main__')
