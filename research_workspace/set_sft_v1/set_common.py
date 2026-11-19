"""新训练身份与文件IO，保留原159模型和所有已冻结实验。"""
import json
from pathlib import Path
from data import MODEL, sha, read

ROOT = Path('/home/yeliheng/grasp_server/set_sft_v1')
PARENT = ROOT.parent
OLD = PARENT/'candidate_sft_v2'
REVIEW = PARENT/'targeted_data_review_v1'
DATA = PARENT/'data_review_v1/output_v1'
SHARDS = 3


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
    temp.replace(path)


def lines(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def reviewed_sources():
    check = read(REVIEW/'independent_verification.json')
    assert check['passed'] and check['complete']
    assert check['manifest_sha256'] == sha(REVIEW/'manifest.json')
    manifest = read(REVIEW/'manifest.json')
    for section in ('code', 'inputs', 'artifacts'):
        assert all(sha(Path(p)) == h for p, h in manifest[section].items())
    assert read(OLD/'verification.json')['passed']
    return manifest


def verify():
    config = read(ROOT/'manifest.json')
    assert config['epochs'] == 1 and config['train_samples'] == 189
    assert config['train_responses'] == 197 and config['accumulation'] == 8
    assert config['objective'] == 'mean_inputs_mean_successes_mean_tokens'
    assert all(sha(Path(p)) == h for p, h in config['identities'].items()), 'Frozen identity drift'
    return config
