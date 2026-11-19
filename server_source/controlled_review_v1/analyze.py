"""从证据生成计数、配对差异和逐失败索引；人工归因单独标注。"""
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path('/home/yeliheng/grasp_server/controlled_review_v1')


def fingerprint(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def request_groups(cases):
    groups = defaultdict(list)
    for case in cases:
        for attempt, event in enumerate(case['arms']['flash']['events'], 1):
            groups[fingerprint(event['request'])].append(dict(case=case['case'], attempt=attempt,
                changes=event.get('parsed', {}).get('changes'), response_text=event.get('text'),
                error=event.get('error'), source=f"{case['case']:02d}/flash/requests.jsonl#{attempt}"))
    return groups


def method_stats(cases, arm):
    rows = [case['arms'][arm]['summary'] for case in cases]
    first_failures = sum(not r['first_success'] for r in rows)
    recoveries = sum(r['success'] and not r['first_success'] for r in rows)
    return dict(tasks=len(rows), successes=sum(r['success'] for r in rows), first_failures=first_failures,
                recoveries=recoveries, recovery_rate=recoveries/first_failures,
                calls=sum(r['calls'] for r in rows), invalid=sum(r['invalid_outputs'] for r in rows),
                service_errors=sum(r['service_errors'] for r in rows))


def comparison(cases):
    result = {key: [] for key in ('both_success', 'flash_only', 'rule_only', 'both_fail')}
    for c in cases:
        flash, rule = (c['arms'][a]['summary']['success'] for a in ('flash', 'rule'))
        key = 'both_success' if flash and rule else 'flash_only' if flash else 'rule_only' if rule else 'both_fail'
        result[key].append(c['case'])
    return result


def failure_rows(cases, annotations):
    result = []
    for case in cases:
        arm = case['arms']['flash']
        if arm['summary']['success']:
            continue
        rows = arm['records']
        item = dict(case=case['case'], **case['task'], rule_success=case['arms']['rule']['summary']['success'],
                    error_chain=' → '.join(r['error']['error_type'] for r in rows),
                    source_file=f"controlled_v3/pilot/tasks/{case['case']:02d}/flash/result.json")
        item.update(annotations[str(case['case'])])
        result.append(item)
    return result


def analyze(data, annotations):
    cases, groups = data['cases'], request_groups(data['cases'])
    failures = failure_rows(cases, annotations['failures'])
    duplicates = [dict(request_sha256=key, rows=value,
                      text_variants=len({r['response_text'] for r in value}),
                      action_variants=len({fingerprint(r['changes']) for r in value}))
                  for key, value in groups.items() if len(value) > 1]
    faults = {fault: dict(Counter(c['arms']['retry']['summary']['first_error'] or 'success'
              for c in cases if c['task']['fault'] == fault)) for fault in ('none', 'calibration', 'collision', 'placement')}
    return dict(methods={arm: method_stats(cases, arm) for arm in ('retry', 'rule', 'flash')},
                comparison=comparison(cases), failures=failures,
                primary_categories=dict(Counter(r['category'] for r in failures)),
                requests=sum(map(len, groups.values())), unique_requests=len(groups), duplicates=duplicates,
                first_errors_by_injected_fault=faults, test_used=False,
                annotation_scope='human interpretations are not experimentally verified counterfactual causes')


def validate(data, analysis):
    cases = data['cases']
    assert len(cases) == 48 and len({c['case'] for c in cases}) == 48
    assert sum(len(c['arms']) for c in cases) == 144
    for arm in ('retry', 'rule', 'flash'):
        for case in cases:
            row = case['arms'][arm]
            assert row['summary']['success'] == any(r['accepted'] for r in row['records'])
            assert row['summary']['calls'] == len(row['feedback'])
            for path, digest in row['source_files'].items():
                assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
    assert analysis['requests'] == 40 and analysis['unique_requests'] == 34
    assert len(analysis['failures']) == 14
    assert sum(map(len, analysis['comparison'].values())) == 48
    assert len(analysis['comparison']['flash_only']) == 5 and len(analysis['comparison']['rule_only']) == 3
    assert analysis['methods']['flash']['invalid'] == 3 and analysis['methods']['flash']['service_errors'] == 0


def markdown(analysis, data, annotations):
    lines = ['# 逐场景证据索引', '', 'case 使用服务器目录中的零基编号；归因置信度见表格。', '',
             '## Flash 的 14 个失败条件', '', '|case|物体/注入/因素|实际错误链|主分类|依据与边界|',
             '|---|---|---|---|---|']
    for row in analysis['failures']:
        lines.append(f"|{row['case']:02d}|{row['source']}/{row['fault']}/{row['level']}|{row['error_chain']}|"
                     f"{row['category']}|{row['finding']} {row['confidence']}|")
    lines += ['', '## Flash 与规则结果不同的 8 个条件', '', '|case|Flash|规则|证据解释|', '|---|---|---|---|']
    for case in data['cases']:
        key = str(case['case'])
        if key in annotations['differences']:
            values = [case['arms'][arm]['summary']['success'] for arm in ('flash', 'rule')]
            lines.append(f"|{case['case']:02d}|{'成功' if values[0] else '失败'}|{'成功' if values[1] else '失败'}|"
                         f"{annotations['differences'][key]}|")
    lines += ['', '## 重复请求', '', '按完整请求负载（含 messages、温度、seed、模型、预算）比较，未删除任何条件。']
    for group in analysis['duplicates']:
        refs = ', '.join(f"case{r['case']:02d}/attempt{r['attempt']}" for r in group['rows'])
        lines.append(f"- {refs}：{group['text_variants']} 种回答文本，{group['action_variants']} 种解析动作。")
    return '\n'.join(lines)+'\n'


def main():
    data = json.loads((ROOT/'review_data.json').read_text())
    annotations = json.loads((ROOT/'annotations.json').read_text())
    result = analyze(data, annotations)
    validate(data, result)
    (ROOT/'analysis.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (ROOT/'CASE_INDEX.md').write_text(markdown(result, data, annotations))
    with (ROOT/'failures.csv').open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(result['failures'][0]))
        writer.writeheader()
        writer.writerows(result['failures'])
    (ROOT/'verification.json').write_text(json.dumps(dict(passed=True, cases=48, runs=144,
        raw_source_hashes_verified=True, annotations_cover_all_flash_failures=True,
        annotations_are_human_analysis=True, test_used=False), indent=2))
    print(json.dumps({k: result[k] for k in ('methods', 'comparison', 'primary_categories', 'first_errors_by_injected_fault')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
