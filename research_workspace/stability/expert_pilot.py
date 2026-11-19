"""只读导入已完成的12组规则/重试轨迹，保留原件与逐文件hash。"""
import hashlib
import argparse
import json
from pathlib import Path
from stability.collection_status import atomic
from stability.experiment import OUT, fingerprint
from stability.expert_config import configuration
from stability.expert_worker import summarize
from stability.expert_audit import audit


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    args = parser.parse_args()
    assert args.run.startswith('expert_pilot_') and '/' not in args.run
    config, directory = configuration('pilot'), OUT/args.run
    rule_manifest = json.loads((OUT/'rule_pilot_v1/manifest.json').read_text())
    retry_manifest = json.loads((OUT/'pilot9_v1/manifest.json').read_text())
    assert rule_manifest['fingerprint'] == retry_manifest['code'] == fingerprint()
    assert retry_manifest['plan'] == config['plan']
    directory.mkdir(exist_ok=True)
    with (directory/'manifest.json').open('x') as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2)
    imports = []
    for index, task in enumerate(config['plan']):
        root = directory/'tasks'/f'{index:05d}'
        expert_path, retry_path = root/'expert/run_000', root/'retry/run_000'
        original = json.loads((OUT/'pilot9_v1/tasks'/f'{index:05d}'/'summary.json').read_text())
        sources = [OUT/'rule_pilot_v1'/f'{index:02d}'/'stable/result.json', Path(original['retry_result'])]
        for source, target in zip(sources, (expert_path, retry_path)):
            target.mkdir(parents=True)
            content = source.read_bytes()
            (target/'result.json').write_bytes(content)
            imports.append({'original': str(source), 'copy': str(target/'result.json'),
                            'sha256': hashlib.sha256(content).hexdigest()})
        summarize(task, root, expert_path=expert_path, retry_path=retry_path)
    atomic(directory/'imports.json', imports)
    result = audit(directory)
    print(json.dumps({'allow_batch': result['allow_batch'], 'status': result['status']}), flush=True)


if __name__ == '__main__':
    main()
