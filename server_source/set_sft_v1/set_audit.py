"""完整训练覆盖、集合评价重算、原口径回放和重载身份最终核验。"""
import json
from objective import score_text
from set_common import ROOT, OLD, SHARDS, read, save, sha, verify


def collect(mode):
    rows, errors = [], []
    for shard in range(SHARDS):
        result = read(ROOT/'evaluation'/mode/f'shard_{shard}/result.json')
        assert result['status'] == 'completed' and result['manifest_sha256'] == sha(ROOT/'manifest.json')
        assert result['reload_error'] <= 1e-4 and not result['test_used']
        rows.extend(result['rows'])
        errors.append(result['reload_error'])
    return rows, errors


def metrics(rows, raw, method):
    group = sorted([r for r in rows if r['method'] == method], key=lambda r:r['index'])
    assert [r['index'] for r in group] == list(range(len(raw)))
    for row, source in zip(group, raw):
        assert row['id'] == source['id'] and row['split'] == source['split']
        assert row['output_tokens'] == len(row['generated_ids']) <= 128
        assert row['finished'] == bool(row['generated_ids'] and row['generated_ids'][-1] in row['eos_ids'])
        ids = [c['id'] for c in json.loads(source['messages'][1]['content'])['candidates']]
        score = score_text(row['text'], candidates=ids, accepted=source['accepted_action_ids'])
        assert row['candidate_valid'] == (score['candidate_valid'] and row['finished'])
        assert row['set_match'] == (score['set_match'] and row['finished'])
        assert row['diagnostic_match'] == bool(row['candidate_valid'] and source.get('diagnostic_target') == score['action_id'])
        assert row['diagnostic_index'] == source['diagnostic_index']
    result = {}
    for split in ('dev','legacy_dev','train_diagnostic'):
        values = [r for r in group if r['split'] == split]
        diagnostic = [r for r in values if r['diagnostic_index'] is not None]
        result[split] = dict(inputs=len(values), candidate_valid=sum(r['candidate_valid'] for r in values),
            set_matches=sum(r['set_match'] for r in values), finished=sum(r['finished'] for r in values),
            mean_input_set_loss=sum(r['loss'] for r in values)/len(values),
            original_subset_n=len(diagnostic), original_subset_matches=sum(r['diagnostic_match'] for r in diagnostic))
    return result


def replay(rows):
    matches = {}
    for method, prior in (('base', 'before'), ('previous159', 'after')):
        original = {}
        for shard in range(SHARDS):
            for row in read(OLD/'evaluation'/prior/f'shard_{shard}/result.json')['rows']:
                original[(row['split'], row['index'])] = row['text']
        current = {(r['split'], r['diagnostic_index']):r['text'] for r in rows
                   if r['method'] == method and r['diagnostic_index'] is not None}
        assert set(current) == set(original) and len(current) == 78
        matches[method] = sum(current[k] == original[k] for k in current)
        assert matches[method] == 78, 'Original 49/29 deterministic replay changed'
    return matches


def training_check():
    result = read(ROOT/'training/result.json')
    assert result['status'] == 'completed' and result['manifest_sha256'] == sha(ROOT/'manifest.json')
    updates = read(ROOT/'training/updates.json')
    assert len(updates) == result['updates'] == 24
    assert sorted(i for r in updates for i in r['indices']) == list(range(189))
    assert sum(r['inputs'] for r in updates) == result['inputs_seen'] == 189
    assert sum(r['responses'] for r in updates) == result['responses_seen'] == 197
    assert all(r['weighting'] == 'mean_inputs_mean_successes_mean_tokens' for r in updates)
    assert result['changed_tensors'] > 0 and updates[-1]['inputs'] == 5
    assert all(sha(ROOT/'training/adapter'/p) == h for p,h in result['adapter_files'].items())
    return result


def report(value):
    text = ['# 189输入多成功动作微调结果', '',
        'Qwen3.5-4B从基础权重独立训练1epoch；189输入、197回复、24次更新。', '',
        '| 模型 | 开发集合命中 | 旧场景集合命中 | 新30训练诊断命中 |', '|---|---:|---:|---:|']
    for method, values in value['metrics'].items():
        cells = [f"{values[s]['set_matches']}/{values[s]['inputs']}" for s in ('dev','legacy_dev','train_diagnostic')]
        text.append('| '+method+' | '+' | '.join(cells)+' |')
    text += ['', '完整候选合法率与原49/29单标签口径见verification.json。训练诊断不能当泛化结果。',
             '集合只包含已经观察到的成功动作，未命中不必然意味着物理失败。',
             '本轮尚未运行新模型物理闭环或预留最终测试。数据量、目标聚合及更新次数都有变化，不能单独归因。']
    (ROOT/'REPORT.md').write_text('\n'.join(text)+'\n')


def main():
    config = verify()
    training = training_check()
    before, first_errors = collect('before')
    after, last_errors = collect('after')
    raw = read(ROOT/'eval.json')
    all_rows = before+after
    results = {m:metrics(all_rows, raw, m) for m in ('base','previous159','new189')}
    assert all({s:v['inputs'] for s,v in values.items()} == config['evaluation_counts'] for values in results.values())
    value = dict(passed=True, complete=True, training=training, metrics=results,
        old_replay_text_matches=replay(before), reload_errors=dict(previous=first_errors, new=last_errors),
        physical_evaluation_started=False, final_test_used=False, manifest_sha256=sha(ROOT/'manifest.json'))
    save(ROOT/'verification.json', value)
    report(value)
    print(json.dumps({k:v for k,v in value.items() if k != 'training'}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'verification_failure.json', dict(passed=False, error=repr(error)))
        raise
