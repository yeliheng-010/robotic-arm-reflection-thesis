import runpy
from reflection.__main__ import bootstrap
bootstrap()
from sv_common import ROOT
from sv_requests_v2 import context


if __name__ == '__main__':
    with context():
        runpy.run_path(str(ROOT/'audit.py'), run_name='__main__')
