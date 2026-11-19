"""汇总独立校准来源和回归结果；只更新派生报告，不更改原始证据。"""
import hashlib
import json
from pathlib import Path
import analyze

ROOT = Path('/home/yeliheng/grasp_server/refinement_v3')


def import_collision():
    source = ROOT.parent/'refinement_v2/collision/result.json'
    destination = ROOT/'collision/result.json'
    destination.parent.mkdir(exist_ok=True)
    content = source.read_bytes()
    destination.write_bytes(content)
    provenance = dict(source=str(source), sha256=hashlib.sha256(content).hexdigest(),
                      job=4740, role='Reused unchanged v2 independent geometry calibration; not repeated runs')
    (destination.parent/'provenance.json').write_text(json.dumps(provenance, indent=2))
    return provenance


def route_lines():
    source = ROOT.parent/'collision_route_v3'
    path = source/'result.json'
    if not path.exists():
        path = source/'progress.json'
    if not path.exists():
        return ['路线校准尚无已落盘结果。'], {}
    content = path.read_bytes()
    value = json.loads(content)
    lines = ['', '紫色胶囊路线校准（独立于模型回归）：', '',
             f"状态 {value['status']}，{len(value['rows'])}/{value['expected']}，障碍 Y=0.84 m、X 范围 1.32—1.395 m。",
             '', '|半高 m|默认成功|目标碰撞|错误|', '|---|---|---|---|']
    for row in value['rows']:
        lines.append(f"|{row['height']}|{row['success']}|{row['intended_collision']}|{row['error']}|")
    lines += ['', '原 Y=0.72 校准作业 4744 因几何与绿色圆柱重叠而停止，记录保留；'
              'Y=0.82 的宽障碍作业 4745 被初始 qpos 审计拦截，说明仅检查四个目标物体不足。'
              '本组使用完整场景中 57 个可接触几何体的边界检查，最小轴向间隔 0.0122 m，并在每次运行后核验初始 qpos。',
              '没有调用模型，也没有按模型恢复结果选择障碍。']
    return lines, {str(path): hashlib.sha256(content).hexdigest()}


def main():
    provenance = import_collision()
    analyze.main(ROOT)
    lines, sources = route_lines()
    with (ROOT/'REPORT.md').open('a') as stream:
        stream.write('\n'.join(lines)+'\n')
    source_path = ROOT/'report_sources.json'
    hashes = json.loads(source_path.read_text())
    hashes.update(sources)
    hashes[provenance['source']] = provenance['sha256']
    source_path.write_text(json.dumps(hashes, indent=2))
    print('Updated derived report; raw experiment files preserved')


if __name__ == '__main__':
    main()
