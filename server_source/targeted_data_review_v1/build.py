"""重新审计源物理证据后导出独立数据包，不修改或启动训练。"""
import json
from pathlib import Path
from collections import Counter
from common import read, save, sha
from pilot_common import ROOT as SOURCE, verify as verify_collection
from audit import audit_scene
from labels import records, summarize, held_inputs
from prepare import partition, sft_row, digest_input
from verify_export import verify, verify_manifest

ROOT = SOURCE.parent/'targeted_data_review_v1'
OUTPUT = ROOT/'output_v1'


def audit_source():
    manifest = verify_collection()
    final = read(SOURCE/'final_verification.json')
    assert final['passed'] and final['complete'] and final['accounted'] == 24
    hashes = {str(SOURCE/p):sha(SOURCE/p) for p in
              ('manifest.json', 'final_verification.json', 'final_node_outcomes.json')}
    rebuilt, checked = [], []
    for scene in manifest['scenes']:
        folder = SOURCE/'tasks'/scene['id']
        value = read(folder/'result.json')
        assert value['scene'] == scene
        summary = audit_scene(value)
        assert summary == read(folder/'summary.json')
        checked.append(summary)
        rebuilt.extend(records(value))
        paths = [folder/'result.json', folder/'summary.json',
                 SOURCE/'qualification'/scene['id']/'result.json']
        for trajectory in value['trajectories']:
            paths.append(Path(trajectory))
            paths.extend(Path(s['result_path']) for s in read(trajectory)['attempts'])
        q = read(paths[2])
        paths.extend(Path(s['result_path']) for s in q['steps'])
        hashes.update({str(p):sha(p) for p in paths})
    assert checked == final['rows'] and sum(r['physical_executions'] for r in checked) == 214
    assert summarize(rebuilt) == final['labels']
    assert rebuilt == read(SOURCE/'final_node_outcomes.json')
    return rebuilt, hashes


def audit_old_data(hashes, held):
    parent = SOURCE.parent/'data_review_v1'
    folder = parent/'output_v1'
    manifest = read(folder/'manifest.json')
    hashes[str(folder/'manifest.json')] = sha(folder/'manifest.json')
    for section, base in (('code', parent), ('artifacts', folder)):
        for filename, expected in manifest[section].items():
            path = base/filename
            assert sha(path) == expected
            hashes[str(path)] = expected
    old = [json.loads(line) for line in (folder/'train_combined.jsonl').read_text().splitlines()]
    inputs = {digest_input(r['messages'][:-1]) for r in old}
    assert len(old) == len(inputs) == 159
    return dict(original_training_inputs=len(inputs),
                original_train_overlap_with_expanded_dev=len(inputs & held))


def export(groups, raw):
    OUTPUT.mkdir(exist_ok=False)
    files = dict(groups, provenance=raw,
                 single_success_sft=[sft_row(r) for r in groups['single_success']])
    for name, rows in files.items():
        path = OUTPUT/(name+'.jsonl')
        path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows))


def write_report(summary):
    lines = ['# 定向监督数据包', '',
        '已重新审计24个条件、214次物理执行，重建45个决策输入并核对原记录。', '',
        '| 文件 | 输入数 | 用途 |', '|---|---:|---|',
        '| positive_sets.jsonl | 30 | 所有成功输入，保留完整已观察成功动作集合 |',
        '| single_success_sft.jsonl | 23 | 单成功聊天格式；与single_success.jsonl逐行对应 |',
        '| multi_success.jsonl | 7 | 多成功集合，不任意选一个为唯一答案 |',
        '| unresolved.jsonl | 15 | 已测试分支未成功，不推断未试候选 |',
        '| provenance.jsonl | 45 | 原始输入、分支结果和物理证据索引 |',
        '| quarantine.jsonl | 0 | 当前无旧输入重合；后续重合进入隔离 |', '',
        '文件是同一数据的不同视图，不能相加。30个正例输入对应38个已观察成功动作，不是38个独立样本。',
        '23个单成功输入中13个立即成功、10个经后续规则修正才最终成功。',
        '数据来自6个新训练种子组，model=null，来源为规则分支搜索；未使用预留测试。',
        '', '## 语义与来源', '',
        'messages保持原选择器输入，不加入隐藏故障值、结果标签或额外审计信息。',
        'accepted_action_ids只覆盖已测试的成功动作；observed_unsuccessful_action_ids只表达该规则后续策略下的失败。',
        'untested_action_ids表示未测试，不能作为负例。tested_outcomes保留立即/终局成功、后续尝试数、轨迹路径与hash。',
        '单成功是“目前只观察到一个成功动作”，不等价于全候选空间唯一正确。',
        '', '## 验证', '', '```json', json.dumps(summary, ensure_ascii=False, indent=2), '```',
        '', '## 训练建议（未执行）', '',
        '建议主方案保留30个输入的成功动作集合；7个多解输入包含新增的候选切换、深度、减速和下降−90°成功证据。',
        ('旧159条加单成功23条可作为182输入的消融方案；主方案159+30为189逻辑输入，需先核定并实现多正例训练目标。'
         if summary['original_train_overlap_with_expanded_dev'] == 0 else
         '旧训练输入与扩展开发输入存在精确重合，须先审查隔离；暂不批准159+30直接合并。'),
        '如将每个成功动作展开成单条回复训练，建议每个原输入总权重相同（每回复权重1/k），避免多解输入被重复加权。',
        '该权重策略尚未实现到原训练器，不能将集合文件直接交给原单标签训练脚本。也不以字符串完全匹配惩罚其他已验证成功动作。',
        '原159条标签是立即整体成功，新集合含延迟成功，须保留来源与语义，并分别报告相应效果。',
        '暂不修改原159条、训练参数、模型或开发/测试划分；本轮没有启动训练或新增物理实验。']
    (ROOT/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    raw, inputs = audit_source()
    held, old_train = held_inputs()
    old = audit_old_data(inputs, held)
    groups = partition(raw, held=held, old_train=old_train)
    export(groups, raw)
    summary = verify(OUTPUT, raw, held=held, old_train=old_train)
    assert summary['counts'] == dict(positive_sets=30, single_success=23,
                                    multi_success=7, unresolved=15, quarantine=0)
    summary.update(old, held_input_count=len(held), exact_new_overlap_with_old_train=0,
        exact_new_overlap_with_dev=0, source_conditions=24, source_physical_executions=214,
        new_physical_executions=0, original_training_modified=False,
        source='expert_counterfactual_rule_continuation', model=None)
    save(ROOT/'summary.json', summary)
    write_report(summary)
    code = {str(p):sha(p) for p in sorted(ROOT.glob('*.py'))+sorted(ROOT.glob('*.sbatch'))}
    artifacts = {str(p):sha(p) for p in sorted(OUTPUT.iterdir())}
    artifacts.update({str(ROOT/p):sha(ROOT/p) for p in ('summary.json', 'REPORT.md')})
    save(ROOT/'manifest.json', dict(code=code, inputs=inputs, artifacts=artifacts))
    assert verify_manifest(ROOT)
    save(ROOT/'verification.json', dict(passed=True, complete=True,
        manifest_sha256=sha(ROOT/'manifest.json'), exported_inputs=45,
        source_conditions_reaudited=24, physical_records_reaudited=214,
        original_files_unchanged=True, training_started=False, test_used=False))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
