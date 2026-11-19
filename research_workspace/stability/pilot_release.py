"""冻结已通过原始轨迹审计的试训子集，保留失败采集的真实状态。"""
import fcntl
import hashlib
import json
from pathlib import Path
import traceback
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.expert_audit import audit_task
from stability.expert_config import configuration
from stability.expert_status import datasets_from


def collect_verified(root, config):
    verified, rejected, hashes = [], [], {}
    for path in sorted((root/'tasks').glob('*/summary.json')):
        summary = json.loads(path.read_text())
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        try:
            audit_task(path.parent, config['plan'][int(path.parent.name)])
        except AssertionError:
            assert not summary['samples'], 'Cannot release a sample failing source audit'
            assert summary['invalid'] > 0, 'Unexpected audit failure requires investigation'
            rejected.append({'task': path.parent.name, 'samples': 0, 'reason': traceback.format_exc()})
            continue
        for key in ('expert_result', 'retry_result'):
            result = Path(summary[key])
            hashes[str(result)] = hashlib.sha256(result.read_bytes()).hexdigest()
        verified.append(summary)
    return verified, rejected, hashes


def main():
    root, target = OUT/'expert_batch_v1', OUT/'pilot_sft_data_v1'
    with (root/'.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        config = json.loads((root/'manifest.json').read_text())
        assert config == configuration('batch')
        verified, rejected, hashes = collect_verified(root, config)
        datasets, duplicates = datasets_from(verified, stage='batch')
        assert all(datasets.values())
        target.mkdir(exist_ok=False)
        files = {}
        for split, rows in datasets.items():
            data = ''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows).encode()
            (target/f'{split}.jsonl').write_bytes(data)
            files[split] = {'sha256': hashlib.sha256(data).hexdigest(), 'samples': len(rows)}
        manifest = {'purpose': 'user_authorized_preliminary_rule_expert_sft', 'files': files,
            'original_batch': str(root), 'original_manifest': config, 'source_hashes': hashes,
            'verified_tasks': len(verified), 'quarantined_zero_sample_tasks': rejected,
            'duplicates_excluded': duplicates, 'test_usage': 'sealed_not_used_for_training_or_selection',
            'original_batch_status': json.loads((root/'status.json').read_text()),
            'formal_count_gate_overridden_for_pilot_only': True}
        atomic(target/'manifest.json', manifest)
        print(json.dumps({'release': str(target), 'files': files, 'quarantined': len(rejected)}), flush=True)


if __name__ == '__main__':
    main()
