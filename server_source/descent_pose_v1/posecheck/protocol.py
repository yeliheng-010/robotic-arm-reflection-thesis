"""冻结新增实现与全部依赖实验，拒绝运行中漂移。"""
import json
from semanticfix2.protocol import verify as previous_verify,sha
from posecheck.design import ROOT,items,configuration


def manifest():
    files = sorted((ROOT/'posecheck').glob('*.py'))+[ROOT/'run.sbatch',ROOT/'test_pose.py']
    return dict(previous=previous_verify(),items=items(),scenarios={r['id']:configuration(r) for r in items()},
                code={str(p):sha(p) for p in files},model_calls=0,training_approved=0,test_used=False)


def verify():
    saved = json.loads((ROOT/'protocol.json').read_text())
    assert saved==json.loads(json.dumps(manifest())), 'Protocol drift'
    return saved


if __name__=='__main__':
    with (ROOT/'protocol.json').open('x') as stream:
        json.dump(manifest(),stream,ensure_ascii=False,indent=2)
