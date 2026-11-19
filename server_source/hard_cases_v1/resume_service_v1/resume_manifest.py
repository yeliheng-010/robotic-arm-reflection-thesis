"""只冻结恢复调度器，原实验协议和资格结果保持原身份。"""
import json
from pathlib import Path
from hardstudy.design import ROOT
from hardstudy.protocol import verify
from semanticfix2.protocol import sha

CONTROL=Path(__file__).resolve().parent


def manifest():
    verify()
    files=sorted(CONTROL.glob('*.py'))+sorted(CONTROL.glob('*.sbatch'))
    return dict(original_protocol=sha(ROOT/'protocol.json'),
        qualification_gate=sha(ROOT/'gate_qualification.json'),
        code={str(p):sha(p) for p in files},
        reason='Original loop smoke failed before dispatch: model connection refused',
        preserve_failed_stage=True,training_approved=0)


def verify_control():
    saved=json.loads((CONTROL/'manifest.json').read_text())
    assert saved==manifest(), 'Recovery scheduler drift'


if __name__=='__main__':
    with (CONTROL/'manifest.json').open('x') as stream:
        json.dump(manifest(),stream,indent=2)
