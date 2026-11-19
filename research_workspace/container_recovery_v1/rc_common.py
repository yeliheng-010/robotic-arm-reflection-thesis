"""模型环境可独立导入的身份、状态和冻结检查。"""
import hashlib
import json
import os
from pathlib import Path

PARENT=Path('/home/yeliheng/grasp_server')
ROOT=PARENT/'container_recovery_v1'
SOURCE=PARENT/'container_layout_v2'
ALIAS='qwen35-container-recovery-base'
PORT=38985
METHODS=('retry','rule','model')
MAX_ATTEMPTS=3
SHARDS=3
WORKER_SECONDS=2400


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+f'.{os.getpid()}.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    temporary.replace(path)


def verify():
    value=read(ROOT/'manifest.json')
    for path,digest in value['identities'].items():
        assert sha(path)==digest,'Frozen source changed: '+path
    assert value['methods']==list(METHODS) and len(value['rows'])==160
    assert not value['test_used'] and not value['training_approved']
    return value


def identity():
    return dict(experiment_sha256=sha(ROOT/'manifest.json'),
        runtime_manifest_sha256=sha(PARENT/'candidate_sft_v2/manifest.json'),
        base='Qwen3.5-4B',adapter_enabled=False)
