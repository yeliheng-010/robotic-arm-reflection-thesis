"""保存实际共享服务配置、引擎身份及本轮代码指纹。"""
import hashlib
import json
from pathlib import Path


def identity():
    config_path = Path('/opt/local-llm/etc/local-llm.json')
    config = json.loads(config_path.read_text())
    engine = Path(config['exe'])
    weights = Path('/home/models/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_S')
    return dict(endpoint='http://127.0.0.1:8080/v1', model='qwen3.8-flash-next',
                config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                engine_sha256=hashlib.sha256(engine.read_bytes()).hexdigest(),
                weights={p.name: p.stat().st_size for p in weights.glob('*.gguf')},
                code={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in Path(__file__).parent.glob('*.py')},
                supervision='evaluation against rule_expert labels; outputs are model generated',
                full_weight_hash_rechecked=False, image_input=False)
