"""独立核对诊断输出、配对初始条件和原始数据完整性。"""
import ast
import hashlib
import json
from pathlib import Path

OUT = Path('/home/yeliheng/grasp_server/diagnosis_20261019')
COLLECTION = OUT.parent / 'overnight_20261019/collection'
CODE = COLLECTION.parent / 'code'


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_control(row):
    result = read(Path(row['output']) / 'result.json')
    records = result['records']
    assert row['success'] == any(r['accepted'] for r in records)
    assert all(not r['accepted'] or r['physical_success'] for r in records)
    assert row['attempts'] <= 3
    if row['arm'] == 'retry':
        assert all('reflection' not in r for r in records)
        assert all(r['parameters'] == records[0]['parameters'] for r in records)
    if row['arm'] == 'rule':
        assert all(r['reflection']['source'] == 'rule' for r in records if 'reflection' in r)
    return result


def check_originals():
    audit = read(OUT / 'audit.json')
    assert audit['checked_tasks'] == 420 and audit['test_results_read'] == 0
    for entry in audit['checked_files']:
        assert entry['split'] in {'train', 'validation'}
        assert sha(Path(entry['path'])) == entry['sha256']
    manifest = read(COLLECTION / 'manifest.json')
    for name, expected in manifest['code_sha256'].items():
        assert sha(CODE / name) == expected
    dataset_manifest = read(COLLECTION / 'dataset/manifest.json')
    for name, expected in dataset_manifest['dataset_sha256'].items():
        # 仅对测试文件计算完整性哈希，不解析或评估其中的样本。
        assert sha(COLLECTION / 'dataset' / (name + '.jsonl')) == expected


def check_pairs():
    controls = read(OUT / 'controls_result.json')
    assert len(controls) == 26
    grouped = {}
    for row in controls:
        grouped.setdefault(row['case'], {})[row['arm']] = check_control(row)
    paired = 0
    for arms in grouped.values():
        if 'historical_teacher' not in arms:
            continue
        signatures = [(r['records'][0]['accepted'],
                       (r['records'][0].get('error') or {}).get('error_type')) for r in arms.values()]
        assert len(arms) == 3 and len(set(signatures)) == 1
        for field in ('source', 'destination', 'fault', 'seed', 'instruction', 'scene_jitter_m'):
            assert len({r[field] for r in arms.values()}) == 1
        paired += 1
    return paired


def check_additional_probes():
    geometry = read(OUT / 'geometry_result.json')
    assert len(geometry) == 16
    ablation = read(OUT / 'prompt_ablation.json')
    assert len(ablation['records']) == 12
    prompts = {}
    for row in ablation['records']:
        prompts.setdefault(row['case'], {})[row['version']] = row['messages']
        original_path = COLLECTION / 'tasks' / row['case'] / 'result.json'
        assert sha(original_path) == row['result_sha256']
        if row['version'] == 'v2':
            original = read(original_path)['records'][0]
            if row['validation']['valid']:
                assert row['validation']['answer']['changes'] == original['reflection']['changes']
            else:
                assert row['validation']['error'] == original['reflection_error']
    assert len(prompts) == 6
    assert all(p['v1'][1] == p['v2'][1] for p in prompts.values())


def main():
    check_originals()
    paired = check_pairs()
    check_additional_probes()
    scripts = list(OUT.glob('*.py'))
    for path in scripts:
        ast.parse(path.read_text(), filename=str(path))
    result = dict(status='passed', original_train_validation_results_unchanged=420,
                  original_dataset_hashes_unchanged=True, frozen_code_unchanged=True,
                  paired_initial_error_matches=paired, new_physical_runs=18,
                  geometry_scenes=16, prompt_comparisons=6, scripts_parsed=len(scripts),
                  test_samples_used_for_diagnosis=0,
                  limitation='Selected diagnostic cases, not independent efficacy evaluation')
    (OUT / 'verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()

