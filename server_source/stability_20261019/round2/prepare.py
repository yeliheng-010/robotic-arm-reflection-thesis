"""只读复核所有来源轨迹，冻结新数据；test仅作数据隔离审计。"""
from collections import Counter
import fcntl
import json
from pathlib import Path
import shutil
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.expert_config import configuration
from stability.expert_status import datasets_from
from stability.recovery_audit import audit_recovered_task
from stability.sft_freeze import code_hashes, file_hash, preflight, MODEL
from stability.sft_model import tokenizer

DATA = OUT/'round2_sft_data_v1'
RUN = OUT/'round2_sft_v1'


def reviewed_rows(root):
    config = json.loads((root/'manifest.json').read_text())
    assert config == configuration('batch'), 'Collection identity changed'
    audit = json.loads((root/'recovery_audit.json').read_text())
    assert audit['source_audit_passed'] and audit['eligible_for_training_review']
    summaries, hashes = [], {}
    for path in sorted((root/'tasks').glob('*/summary.json')):
        audit_recovered_task(path.parent, config['plan'][int(path.parent.name)])
        summary = json.loads(path.read_text())
        summaries.append(summary)
        for item in (path, Path(summary['expert_result']), Path(summary['retry_result'])):
            hashes[str(item)] = file_hash(item)
    rows, duplicates = datasets_from(summaries, stage='batch')
    assert len(summaries) == audit['audited_tasks'] == 2345
    assert sum(map(len, rows.values())) == audit['raw_verified_samples'] == 1512
    assert not duplicates
    return rows, hashes


def freeze_data(root):
    assert not DATA.exists() and not RUN.exists(), 'Preserve previous experiment'
    rows, hashes = reviewed_rows(root)
    files, groups, prompts = {}, {}, {}
    DATA.mkdir()
    for split, expected in rows.items():
        original = root/'dataset'/f'{split}.jsonl'
        actual = [json.loads(line) for line in original.read_text().splitlines()]
        assert actual == expected, 'Export differs from reviewed trajectories'
        groups[split] = {(r['metadata']['source'], r['metadata']['destination']) for r in actual}
        prompts[split] = {r['metadata']['prompt_sha256'] for r in actual}
        shutil.copyfile(original, DATA/f'{split}.jsonl')
        files[split] = dict(sha256=file_hash(original), samples=len(actual),
            by_fault=dict(Counter(r['metadata']['fault'] for r in actual)))
    for a, b in (('train', 'validation'), ('train', 'test'), ('validation', 'test')):
        assert not groups[a] & groups[b] and not prompts[a] & prompts[b], 'Split leakage'
    assert [files[s]['samples'] for s in ('train', 'validation', 'test')] == [1002, 294, 216]
    assert min(files['train']['by_fault'].values()) >= 100
    atomic(DATA/'manifest.json', dict(purpose='expanded_rule_expert_sft', files=files,
        source_hashes=hashes, source_audit_sha256=file_hash(root/'recovery_audit.json'),
        original_batch=str(root), source='rule_expert', model=None,
        test_usage='integrity_and_split_audit_only_no_model_evaluation'))


def source_identity():
    source = Path(__file__).parent
    own = {str(p): file_hash(p) for p in source.glob('*.py')}
    extra = ('sft_validate.py',)
    own.update({str(OUT/'stability'/n): file_hash(OUT/'stability'/n) for n in extra})
    return own


def main():
    root = OUT/'expert_batch_v1'
    with (root/'.collector.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        freeze_data(root)
    stats = preflight(DATA, tokenizer(MODEL))
    config = dict(purpose='expanded_rule_expert_qlora_epoch1_not_final_test',
        model=str(MODEL), dataset=str(DATA), output=str(RUN), epochs=1, seed=42,
        rank=8, learning_rate=1e-4, accumulation=8, max_length=4096,
        amp_init_scale=256, checkpoint_interval=25, test_used=False, preflight=stats,
        dataset_manifest_sha256=file_hash(DATA/'manifest.json'), code=code_hashes(),
        source_identity=source_identity(),
        model_files={p.name: file_hash(p) for p in MODEL.iterdir() if p.is_file()})
    RUN.mkdir()
    atomic(RUN/'manifest.json', config)
    print(json.dumps({'output': str(RUN), 'preflight': stats, 'audited_tasks': 2345}), flush=True)


if __name__ == '__main__':
    main()
