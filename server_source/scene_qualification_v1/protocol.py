"""冻结新场景清单，并保留原碰撞实现指纹。"""
import hashlib
import importlib.util
import json
from pathlib import Path
from design import items,build

ROOT = Path('/home/yeliheng/grasp_server/scene_qualification_v1')
REFERENCE = ROOT.parent/'collision_validation_v1/calibrate.py'
spec = importlib.util.spec_from_file_location('collision_reference',REFERENCE)
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


def configuration():
    reference.verify()
    files = sorted(ROOT.glob('*.py'))+sorted(ROOT.glob('*.sbatch'))+[REFERENCE]
    return dict(code={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
                items=items(),scenarios={i['id']:build(i['seed'],i['factor']) for i in items()},
                test_used=False,eligibility='control_success_and_paired_target_contact_at_lift_or_transport')


def verify():
    saved = json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(configuration())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(configuration(),stream,ensure_ascii=False,indent=2)
