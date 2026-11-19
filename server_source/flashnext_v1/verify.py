"""独立重算本轮离线指标和闭环审计，不修改运行中的代码。"""
import hashlib
import json
from pathlib import Path
from reflection.reflector import Parameters
from flashnext.client import check_response, parse_correction
from flashnext.audit import audit_case
from flashnext.validation import dataset, metrics

ROOT = Path('/home/yeliheng/grasp_server/flashnext_v1')


def read(path):
    return json.loads(path.read_text())


def validate_offline():
    directory = ROOT/'validation256'
    result = read(directory/'result.json')
    assert result['status'] == 'completed' and result['expected_samples'] == 294
    rows, digest = dataset()
    assert digest == result['validation_sha256'] and result['test_used'] is False
    events = [json.loads(s) for s in (directory/'responses.jsonl').read_text().splitlines()]
    assert [e['index'] for e in events] == list(range(294))
    for row, event in zip(rows, events):
        assert event['request']['messages'] == row['messages'][:-1]
        assert event['request']['max_tokens'] == 256
        assert event['request']['temperature'] == 0 and event['request']['seed'] == 42
        assert event['request']['chat_template_kwargs'] == {'enable_thinking': False}
        assert event['expected'] == json.loads(row['messages'][-1]['content'])
        assert event['metadata'] == row['metadata']
        verify_scores(event, row)
    assert metrics(events) == result['metrics']
    for name, digest in result['provenance']['code'].items():
        assert hashlib.sha256((ROOT/'flashnext'/name).read_bytes()).hexdigest() == digest
    return dict(passed=True, samples=len(events), metrics=metrics(events), test_used=False)


def verify_scores(event, row):
    exact, json_with_changes, legal = False, False, False
    try:
        raw = event['response']['choices'][0]['message']['content']
        parsed = json.loads(raw)
        json_with_changes = isinstance(parsed, dict) and isinstance(parsed.get('changes'), dict)
        exact = json_with_changes and parsed['changes'] == event['expected']['changes']
    except (KeyError, IndexError, ValueError, TypeError):
        pass
    try:
        text = check_response(event['response'])
        payload = json.loads(row['messages'][1]['content'])
        count = payload['error']['evidence'].get('diagnostics', {}).get('available_candidate_count')
        answer = parse_correction(text, Parameters().updated(payload['parameters']), candidate_count=count)
        assert answer.to_dict() == event['parsed']
        legal = True
    except (KeyError, IndexError, ValueError, TypeError):
        pass
    assert (exact, json_with_changes, legal) == (event['exact'], event['json_with_changes'], event['legal'])


def validate_loop():
    directory = ROOT/'closed_loop1024'
    result, manifest = read(directory/'result.json'), read(directory/'manifest.json')
    assert result['status'] == 'completed' and result['completed'] == 18
    assert result['test_used'] is False
    audits = [audit_case(i, task) for i, task in enumerate(manifest['tasks'])]
    assert audits == result['audits']
    for row in result['rows']:
        path = directory/'tasks'/f"{row['case']:02d}"/row['arm']/'result.json'
        trajectory = read(path)
        assert trajectory['success'] == row['success']
        assert trajectory['attempts'] == row['attempts']
    return dict(passed=True, tasks=18, audits=audits, test_used=False)


def report():
    offline = read(ROOT/'validation256/result.json')
    loop = read(ROOT/'closed_loop1024/result.json')
    score = offline['metrics']
    lines = ['# Flash-Next 任务接入结果', '',
             '离线和闭环作业均完成，独立核验通过。', '',
             f"离线：{score['samples']} 条，合法修正 {score['legal']}，严格参数匹配 {score['exact']}，"
             f"截断 {score['truncated']}，服务错误 {score['service_errors']}。", '',
             '| 闭环组 | 场景数 | 成功数 | 模型/规则调用 | 非法修正 |',
             '|---|---:|---:|---:|---:|']
    for arm, value in loop['metrics'].items():
        lines.append(f"| {arm} | {value['tasks']} | {value['successes']} | {value['calls']} | {value['invalid']} |")
    lines.extend(['', '离线输出上限 256 token；闭环 Flash 为 1024 token、最多 3 次尝试。',
                  '这是 6 个开发场景的仿真结果，不是实机或封存测试结果。输入含仿真真值残差。',
                  '严格参数匹配不等同于物理成功；未用本轮输出训练模型；216 条封存 test 未读取。',
                  '原始证据见 validation256/、closed_loop1024/ 和 delivery_verification.json。'])
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n')


if __name__ == '__main__':
    result = {'offline': validate_offline(), 'closed_loop': validate_loop()}
    target = ROOT/'delivery_verification.json'
    with target.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    report()
    print(json.dumps(result))

