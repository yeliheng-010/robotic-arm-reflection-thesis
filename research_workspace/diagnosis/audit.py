"""审计训练和验证轨迹；不读取冻结测试轨迹，不修改原始结果。"""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

SERVER = Path('/home/yeliheng/grasp_server')
COLLECTION = SERVER / 'overnight_20261019/collection'
CODE = SERVER / 'overnight_20261019/code'
OUTPUT = SERVER / 'diagnosis_20261019'
PERSISTENT = {'calibration', 'collision', 'placement'}


def read_json(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def new_stats():
    return dict(tasks=0, success=0, first_success=0, recovered=0,
                first_errors=Counter(), all_errors=Counter(), invalid=Counter(),
                changes=Counter(), repeated_changes_tasks=0, no_op_changes=0,
                error_correction=defaultdict(Counter), objects=defaultdict(Counter),
                destinations=defaultdict(Counter), first_error_messages=Counter())


def correction_metrics(stats, record):
    reflection = record.get('reflection')
    if not reflection:
        return None
    changes = reflection['changes']
    key = json.dumps(changes, sort_keys=True)
    stats['changes'][key] += 1
    params = record['parameters']
    stats['no_op_changes'] += all(params[k] == v for k, v in changes.items())
    error = record.get('error') or {}
    kind = error.get('error_type', 'none')
    metrics = stats['error_correction'][kind]
    metrics['responses'] += 1
    metrics['increased_lift'] += changes.get('lift_height', params['lift_height']) > params['lift_height']
    metrics['changed_grasp_offset'] += 'grasp_offset' in changes
    metrics['changed_place_offset'] += 'place_offset' in changes
    for residual_key, offset_key in [('grasp_residual_xy', 'grasp_offset'),
                                     ('placement_residual_xy', 'place_offset')]:
        residual = error.get('evidence', {}).get(residual_key)
        if residual is None or offset_key not in changes:
            continue
        delta = [changes[offset_key][i] - params[offset_key][i] for i in range(2)]
        alignment = sum(delta[i] * residual[i] for i in range(2))
        label = 'opposes_residual' if alignment < 0 else 'same_direction_or_zero'
        metrics[offset_key + '_' + label] += 1
    return key


def update(stats, result):
    records = result['records']
    stats['tasks'] += 1
    stats['success'] += result['success']
    stats['first_success'] += records[0]['accepted']
    stats['recovered'] += result['success'] and not records[0]['accepted']
    first_error = records[0].get('error') or {}
    stats['first_errors'][first_error.get('error_type', 'success')] += 1
    stats['first_error_messages'][first_error.get('message', 'success')] += 1
    for field, source in [('objects', 'source'), ('destinations', 'destination')]:
        stats[field][result[source]]['tasks'] += 1
        stats[field][result[source]]['success'] += result['success']
    changes = []
    for record in records:
        stats['all_errors'][(record.get('error') or {}).get('error_type', 'success')] += 1
        if 'reflection_error' in record:
            stats['invalid'][record['reflection_error']] += 1
        value = correction_metrics(stats, record)
        if value is not None:
            changes.append(value)
    stats['repeated_changes_tasks'] += len(changes) >= 2 and changes[0] == changes[1]


def compact_case(index, task, result):
    records = []
    for record in result['records']:
        error = record.get('error') or {}
        records.append(dict(attempt=record['attempt'], accepted=record['accepted'],
                            error_type=error.get('error_type'), message=error.get('message'),
                            evidence=error.get('evidence'), parameters=record['parameters'],
                            reflection=record.get('reflection'), invalid=record.get('reflection_error')))
    return dict(id=f'{index:05d}', task=task, success=result['success'], records=records)


def audit_overnight():
    plan = read_json(COLLECTION / 'plan.json')
    stats, cases, checked = {}, [], []
    selected = {0, 8, 16, 17, 24, 25, 32, 64, 136, 144, 152, 376}
    for index, task in enumerate(plan):
        if task['split'] not in {'train', 'validation'}:
            continue
        path = COLLECTION / 'tasks' / f'{index:05d}' / 'result.json'
        result = read_json(path)
        assert all(result[k] == task[k] for k in ('seed', 'source', 'destination', 'fault', 'instruction'))
        assert result['success'] == any(r['accepted'] for r in result['records'])
        update(stats.setdefault(task['fault'], new_stats()), result)
        checked.append(dict(path=str(path), sha256=digest(path), split=task['split']))
        if index in selected:
            cases.append(compact_case(index, task, result))
    assert len(checked) == sum(t['split'] in {'train', 'validation'} for t in plan)
    return stats, cases, checked


def audit_pilot():
    stats = {}
    for path in sorted((SERVER / 'collections/pilot_v1/tasks').glob('*/result.json')):
        result = read_json(path)
        update(stats.setdefault(result['fault'], new_stats()), result)
    return stats


def write_overview(report):
    lines = ['# 失败归因审计', '', '范围：夜间训练与验证轨迹；冻结测试轨迹未读取。', '',
             '| 故障 | 任务 | 首次成功 | 失败后恢复 | 最终成功 | 非法反思 |',
             '| --- | ---: | ---: | ---: | ---: | ---: |']
    for fault, s in report['overnight'].items():
        lines.append(f"| {fault} | {s['tasks']} | {s['first_success']} | {s['recovered']} | {s['success']} | {sum(s['invalid'].values())} |")
    lines += ['', '详细统计、实例、原始文件 SHA256 见 audit.json。', '',
              '反思后的成功是关联证据；需配对重试对照，不能直接解释为因果收益。',
              '偏移量与残差的点积只检查方向，不证明物理执行一定恢复。',
              'pilot 与 overnight 的对象、种子、指令和提示词不同，不能直接归因于提示词退化。']
    (OUTPUT / 'AUDIT.md').write_text('\n'.join(lines) + '\n')


def main():
    OUTPUT.mkdir(exist_ok=True)
    manifest = read_json(COLLECTION / 'manifest.json')
    mismatches = [name for name, expected in manifest['code_sha256'].items()
                  if digest(CODE / name) != expected]
    assert not mismatches, f'Frozen code changed: {mismatches}'
    stats, cases, checked = audit_overnight()
    report = dict(scope='train_validation_only', test_results_read=0,
                  checked_tasks=len(checked), overnight=stats, pilot=audit_pilot(),
                  cases=cases, checked_files=checked, frozen_code_matches=True,
                  source_manifest_sha256=digest(COLLECTION / 'manifest.json'),
                  script_sha256=digest(Path(__file__)))
    (OUTPUT / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    write_overview(report)
    print(json.dumps({k: report[k] for k in ('scope', 'test_results_read', 'checked_tasks', 'frozen_code_matches')}))
    print((OUTPUT / 'AUDIT.md').read_text())


if __name__ == '__main__':
    main()

