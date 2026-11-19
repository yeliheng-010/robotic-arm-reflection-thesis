"""固定场景、划分、代码及资格筛选逻辑，禁止观察结果后换种子。"""
import json
from semanticfix2.protocol import sha
from noisyloop.protocol import verify as previous_verify
from expand.design import ROOT,scenes,items,configuration,RESERVED_TEST_SEEDS,MAX_ATTEMPTS


def manifest():
    previous=previous_verify()
    completed=json.loads((ROOT.parent/'noisy_loop_v1/verification.json').read_text())
    assert completed['passed'] and completed['complete'] and completed['completed']==144
    files=sorted((ROOT/'expand').glob('*.py'))+sorted(ROOT.glob('*.sbatch'))+sorted(ROOT.glob('test_*.py'))
    files += [ROOT.parent/folder/name for folder,name in
              (('route_loop_v1','verify.py'),('route_loop_v1','compare.py'),('noisy_loop_v1','verify.py'))]
    rows=scenes()
    return dict(previous=previous,code={str(p):sha(p) for p in files},scenes=rows,items=items(),
        scenarios={r['id']:configuration(r) for r in rows},reserved_test_seeds=RESERVED_TEST_SEEDS,
        max_attempts=MAX_ATTEMPTS,qualification_budget=200,training_approved=0,test_used=False)


def verify():
    saved=json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(manifest())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(manifest(),stream,ensure_ascii=False,indent=2)
