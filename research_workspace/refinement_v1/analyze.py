"""只读分析已落盘证据；不参与冻结执行逻辑。"""
import argparse
import hashlib
import json
from pathlib import Path


def load(root, stage):
    for filename in ('result.json', 'progress.json'):
        path = root/stage/filename
        if path.exists():
            return json.loads(path.read_text()), path
    return None, None


def diagnostic_lines(data):
    lines = ['', '|诊断|提示|合法回答|合法动作种数|', '|---|---|---:|---:|']
    for row in data.get('summary', []):
        lines.append(f"|{row['label']}|{row['variant']}|{row['legal']}/{row['calls']}|{row['unique_legal_actions']}|")
    lines += ['', '合法性不等于语义正确或物理成功；动作种数用于检查同输入的一致性。',
              'direction_dot_products 为拟议抓取位移与展示残差的内积，负值仅支持方向一致，不能代替物理执行。']
    return lines


def physical_lines(data):
    lines = ['', '|方法|成功/运行|条件数|无效输出|策略耗尽|', '|---|---:|---:|---:|---:|']
    for arm in ('rule_old', 'rule_new', 'flash_old', 'flash_new'):
        rows = [r for r in data.get('rows', []) if r['arm'] == arm]
        lines.append(f"|{arm}|{sum(r['success'] for r in rows)}/{len(rows)}|"
                     f"{len({r['case'] for r in rows})}|{sum(r['invalid_outputs'] for r in rows)}|"
                     f"{sum(r['policy_exhausted'] for r in rows)}|")
    lines += ['', '模型每条件重复三次，重复不是独立场景样本；需按条件聚合比较，不直接把 36 次当作 36 个独立条件。',
              '这些条件来自已知失败复盘，只能作开发回归，不能据此宣称测试集泛化。']
    return lines


def collision_lines(data):
    lines = ['', '|条件|半高 m|默认成功|目标障碍碰撞|错误|', '|---|---:|---|---|---|']
    for row in data.get('rows', []):
        lines.append(f"|{row['case']}|{row['height']}|{row['success']}|{row['intended_collision']}|{row['error']}|")
    lines += ['', 'None 为禁用障碍物对照；0.06 m 为原始低障碍物。其他高度按预定网格扫描。',
              '目标碰撞要求 collision 错误的接触对明确包含 SafetyDivider；单纯抓取失败不算有效碰撞注入。',
              '保留所有未触发条件。该扫描不与原场景语义回归混合，且未用任何模型恢复结果挑选几何。']
    return lines


def main(root):
    lines = ['# 参数语义、专家规则与碰撞校准', '',
             '范围：36 次离线诊断、8 次物理预检、96 次开发回归、12 次独立碰撞校准。',
             '未启动 192 条件扩展或微调；封存测试未使用。', '',
             'rule_new 的缺失测量探测来自显式专家规则；flash_new 仅追加通用参数语义，未修补模型回答。']
    hashes = {}
    for stage, formatter in (('diagnostic', diagnostic_lines), ('smoke', physical_lines),
                             ('regression', physical_lines), ('collision', collision_lines)):
        data, path = load(root, stage)
        if data is None:
            lines += ['', f'{stage}：尚无已落盘结果。']
            continue
        hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        completed = data.get('completed', len(data.get('rows', [])))
        lines += ['', f"{stage}：{data['status']}，{completed}/{data['expected']}。"]
        lines += formatter(data)
    (root/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    (root/'report_sources.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    main(parser.parse_args().root)
