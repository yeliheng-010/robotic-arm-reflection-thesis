"""数组结束后仅汇总已有结果，不调用仿真或重试。"""
from collections import Counter
from pathlib import Path
from qualified_closure_dynamics_v1.protocol import read, save

ROOT = Path(__file__).resolve().parent


def group(rows, planned):
    attempts = sum(row.get('physical_attempts', 0) for row in rows)
    success = sum(row.get('success') is True for row in rows)
    engineering = sum(row.get('status') == 'engineering_failure' for row in rows)
    return dict(planned=planned, records=len(rows), physical_attempts=attempts, successes=success,
        success_fraction_of_attempts=success / attempts if attempts else None,
        success_fraction_of_planned=success / planned, engineering_failures=engineering,
        statuses=dict(Counter(row['status'] for row in rows)),
        last_stages=dict(Counter((row.get('stages') or ['not_started'])[-1] for row in rows)))


def main():
    manifest = read(ROOT / 'manifest.json')
    rows, missing, malformed = [], [], []
    for condition in manifest['conditions']:
        path = ROOT / 'run' / f"{condition['index']:03d}" / 'result.json'
        if not path.exists():
            missing.append(condition['index'])
            continue
        try:
            row = read(path)
            row['condition'] = condition
            rows.append(row)
        except Exception as error:
            malformed.append(dict(index=condition['index'], error=str(error)))
    summary = group(rows, len(manifest['conditions']))
    summary.update(missing=missing, malformed=malformed, complete=not missing and not malformed,
        stopped=(ROOT / 'STOP.json').exists(), scope=manifest['scope'],
        by_radius_mm={str(radius): group([r for r in rows if r['condition']['radius_mm'] == radius], 40)
                      for radius in manifest['radii_mm']},
        note='Fixed-scene deterministic position sweep; not model or unseen-scene generalization.')
    save(ROOT / 'summary.json', summary)
    save(ROOT / 'all_results.json', rows)
    lines = ['# 批量抓放结果', '', f"计划条件：{summary['planned']}",
        f"结果记录：{summary['records']}；实际任务尝试：{summary['physical_attempts']}",
        f"成功：{summary['successes']}；缺失：{len(missing)}；损坏：{len(malformed)}", '',
        '固定场景与固定动作的位置扰动扫描，不代表模型或未见场景泛化。', '',
        '|偏移半径/mm|尝试|成功|尝试内成功比例|', '|---|---|---|---|']
    for radius, row in summary['by_radius_mm'].items():
        rate = row['success_fraction_of_attempts']
        value = 'N/A' if rate is None else f'{rate:.1%}'
        lines.append(f"|{radius}|{row['physical_attempts']}|{row['successes']}|{value}|")
    with (ROOT / 'RESULTS.md').open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(lines) + '\n')
    print(summary, flush=True)


if __name__ == '__main__':
    main()
