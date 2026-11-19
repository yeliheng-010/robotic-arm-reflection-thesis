"""冻结新增代码、参考初态和资格证据；旧协议保持只读。"""
import hashlib
import json
from pathlib import Path
from bounded.protocol import verify as bounded_verify
from recovery.references import BASE,SCENES,scene_protocol
from recovery.design import runs,configuration,smoke_ids

ROOT = BASE/'recovery_study_v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reference_path(item):
    if item['study']=='feedback':
        return BASE/'bounded_reflection_v1/physical/tasks/47_retry_0/result.json'
    return SCENES/'runs'/item['scene_id']/'1/result.json'


def configuration_manifest():
    previous = bounded_verify()
    scenes = scene_protocol.verify()
    files = list((ROOT/'recovery').glob('*.py'))+list(ROOT.glob('*.sbatch'))+[ROOT/'test_study.py']
    items = runs()
    evidence = json.loads((SCENES/'verification.json').read_text())
    qualified = {r['id'] for r in evidence['rows'] if r['qualified']}
    assert all(r['scene_id'] in qualified for r in items if r['study']=='collision')
    references = sorted({reference_path(r) for r in items})
    return dict(previous=previous,scene_protocol=scenes,code={str(p):sha(p) for p in sorted(files)},
                items=items,scenarios={r['id']:configuration(r) for r in items},
                references={str(p):sha(p) for p in references},
                qualification_sha256=sha(SCENES/'verification.json'),smoke=smoke_ids(),
                test_used=False,training_approved=0)


def verify():
    value = json.loads((ROOT/'protocol.json').read_text())
    assert value==json.loads(json.dumps(configuration_manifest())), 'Protocol drift'
    return value


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(configuration_manifest(),stream,ensure_ascii=False,indent=2)
