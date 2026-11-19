"""在提交前冻结程序和任务；启动和每条任务前核验依赖不漂移。"""
import hashlib
import json
from pathlib import Path
from stability.experiment import BASE, fingerprint
from controlled.config import ARMS, MAX_ATTEMPTS, MAX_TOKENS, VERSION, tasks, scenario
from controlled.worker import ROOT

DEPENDENCIES = ('controlled_v3/controlled', 'diversity_v1/diversity', 'flashnext_v1/flashnext',
                'stability_20261019/stability', 'geometry_20261019/geometry')


def source_hashes():
    paths = [p for directory in DEPENDENCIES for p in (ROOT.parent/directory).glob('*.py')]
    paths.extend((BASE/'reflection').glob('*.py'))
    paths.extend((BASE/'training/refine').glob('*.py'))
    paths.extend((BASE/'training/qlora').glob('*.py'))
    paths.extend((ROOT/'controlled').glob('*.sbatch'))
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def configuration():
    return dict(version=VERSION, code=source_hashes(), physics=fingerprint(), tasks=tasks(), arms=list(ARMS),
                scenarios=[scenario(t['seed'], t['level']) for t in tasks()],
                max_attempts=MAX_ATTEMPTS, max_tokens=MAX_TOKENS, test_used=False)


def verify():
    value = json.loads((ROOT/'protocol.json').read_text())
    assert value == configuration(), 'Frozen code/protocol changed; create a new experiment version'
    return value


if __name__ == '__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(configuration(), stream, ensure_ascii=False, indent=2)
    with (ROOT/'expansion_plan.json').open('x') as stream:
        json.dump(dict(status='planned_not_executed', tasks=tasks(expanded=True), test_used=False), stream, indent=2)
    print('Frozen 48 conditions; expanded 192 are planned only')
