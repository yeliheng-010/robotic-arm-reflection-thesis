"""独立检查完整epoch、恢复记录、数据身份及全量生成覆盖。"""
from collections import Counter
import json
import math
from pathlib import Path
from stability.collection_status import atomic
from stability.experiment import OUT
from stability.sft_freeze import file_hash, code_hashes

RUN = OUT/'round2_sft_v1'


def read(path):
    return json.loads(path.read_text())


def verify_identity(config):
    assert config['code'] == code_hashes()
    for path, expected in config['source_identity'].items():
        assert file_hash(Path(path)) == expected
    dataset = Path(config['dataset'])
    assert file_hash(dataset/'manifest.json') == config['dataset_manifest_sha256']
    manifest = read(dataset/'manifest.json')
    for split, info in manifest['files'].items():
        assert file_hash(dataset/f'{split}.jsonl') == info['sha256']
        original = Path(manifest['original_batch'])/'dataset'/f'{split}.jsonl'
        assert file_hash(original) == info['sha256']
    return manifest


def training_result():
    result = read(RUN/'result.json')
    assert result['status'] == 'completed' and result['test_used'] is False
    updates = result['updates']
    assert len(updates) == 126 and result['train_samples_seen'] == 1002
    assert [r['step'] for r in updates] == list(range(1, 127))
    assert sorted(i for row in updates for i in row['indices']) == list(range(1002))
    assert sum(row['samples'] for row in updates) == 1002 and updates[-1]['samples'] == 2
    assert result['resume_events'][0]['restored_step'] == 1
    assert result['resume_events'][0]['fresh_process'] is True
    assert math.isfinite(result['adapter_reload_max_logit_error'])
    assert result['adapter_reload_max_logit_error'] <= .02
    assert read(RUN/'pause_result.json')['status'] == 'checkpointed'
    assert result['changed_adapter_tensors'] > 0
    for name, expected in result['adapter_files'].items():
        assert file_hash(RUN/'adapter'/name) == expected
    return result


def validation_arm(arm, config):
    rows = []
    for shard in range(2):
        part = read(RUN/f'validation_{arm}_{shard}.json')
        assert part['status'] == 'completed' and part['arm'] == arm
        assert part['shard'] == shard and part['shards'] == 2 and not part['test_used']
        assert part['dataset_manifest_sha256'] == config['dataset_manifest_sha256']
        assert part['manual_loss_check']['difference'] < 1e-6
        if arm == 'adapted':
            assert part['adapter_sha256'] == file_hash(RUN/'adapter/adapter_model.safetensors')
        rows.extend(part['results'])
    rows.sort(key=lambda row: row['index'])
    assert [r['index'] for r in rows] == list(range(294))
    source = Path(config['dataset'])/'validation.jsonl'
    expected_rows = [json.loads(line) for line in source.read_text().splitlines()]
    assert len(expected_rows) == len(rows)
    for row, expected in zip(rows, expected_rows):
        assert row['expected'] == json.loads(expected['messages'][-1]['content'])
        assert row['task_id'] == expected['metadata']['task_id']
        assert row['fault'] == expected['metadata']['fault']
        try:
            answer = json.loads(row['raw_output'])
            valid = isinstance(answer, dict) and isinstance(answer.get('changes'), dict)
            exact = valid and answer['changes'] == row['expected']['changes']
        except ValueError:
            valid, exact = False, False
        assert row['json_with_changes'] == valid and row['changes_exact_match'] == exact
    atomic(RUN/f'validation_{arm}_all.json', dict(arm=arm, samples=294, results=rows))
    return rows


def main():
    config = read(RUN/'manifest.json')
    manifest = verify_identity(config)
    trained = training_result()
    arms = {arm: validation_arm(arm, config) for arm in ('base', 'adapted')}
    for base, adapted in zip(arms['base'], arms['adapted']):
        assert (base['task_id'], base['expected']) == (adapted['task_id'], adapted['expected'])
    metrics = {arm: dict(samples=len(rows), json_with_changes=sum(r['json_with_changes'] for r in rows),
        changes_exact_match=sum(r['changes_exact_match'] for r in rows),
        matching_by_fault=dict(Counter(r['fault'] for r in rows if r['changes_exact_match'])))
        for arm, rows in arms.items()}
    report = dict(passed=True, training=dict(samples=1002, epoch=1, updates=126,
        changed_adapter_tensors=trained['changed_adapter_tensors'],
        validation_before=trained['validation_before'], validation_after=trained['validation_after'],
        reload_max_logit_error=trained['adapter_reload_max_logit_error'],
        resumed_in_fresh_process=trained['resume_events']), validation=metrics,
        data_files=manifest['files'], test_used=False, physics_evaluated=False,
        verifier_sha256=file_hash(Path(__file__)),
        scope='Rule-label validation, not physical success or independent final test')
    atomic(RUN/'delivery_verification.json', report)
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
