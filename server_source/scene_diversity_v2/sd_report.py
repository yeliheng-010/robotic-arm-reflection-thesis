"""聚合已冻结实验，生成实际渲染拼图和可审计报告。"""
import json
import cv2
import numpy as np
from sd_config import ROOT, GROUPS, SEEDS
from sd_common import read, save, sha, verify


def montage():
    rows = []
    for seed in SEEDS[:4]:
        images = []
        for group in GROUPS:
            image = cv2.imread(str(ROOT/'renders'/f'{seed}_{group}'/'rgb.png'))
            assert image is not None
            image = cv2.resize(image, (320,320))
            label = np.full((38,320,3), 245, dtype=np.uint8)
            cv2.putText(label, f'{seed} {group}', (8,24), cv2.FONT_HERSHEY_SIMPLEX, .48, (20,20,20), 1)
            images.append(np.vstack((label,image)))
        rows.append(np.hstack(images))
    assert cv2.imwrite(str(ROOT/'scene_grid.jpg'), np.vstack(rows))


def limits(rows, key):
    values = [row[key] for row in rows]
    return [min(values), max(values)]


def diversity(manifest):
    layouts = list(manifest['layouts'].values())
    moves = [d for layout in layouts for d in layout['displacements'].values()]
    cameras = [manifest['configs'][f'{seed}_camera']['camera'] for seed in SEEDS]
    return dict(layouts=len(layouts), moved_bodies=len(moves),
        displacement_m=dict(min=min(moves), median=float(np.median(moves)), max=max(moves)),
        layouts_all_moves_ge_20cm=sum(min(row['displacements'].values())>=.20 for row in layouts),
        azimuth_offset_deg=limits(cameras, 'azimuth_offset_deg'),
        elevation_deg=limits(cameras, 'elevation_deg'), fovy_deg=limits(cameras, 'fovy'))


def appearance_invariance():
    rows = []
    for seed in SEEDS[:6]:
        for before, after in (('baseline','appearance'), ('layout_camera','combined')):
            a = ROOT/'renders'/f'{seed}_{before}'
            b = ROOT/'renders'/f'{seed}_{after}'
            with np.load(a/'sensor.npz') as x, np.load(b/'sensor.npz') as y:
                equal = np.array_equal(x['depth'], y['depth']) and np.array_equal(x['roots'], y['roots'])
            rows.append(dict(seed=seed, pair=[before,after], same_geometry_sensor=equal,
                             different_rgb=sha(a/'rgb.png')!=sha(b/'rgb.png')))
    assert all(row['same_geometry_sensor'] and row['different_rgb'] for row in rows)
    return rows


def main():
    manifest = verify()
    result = read(ROOT/'final_verification.json')
    assert result['passed'] and result['complete'] and result['accounted']==144
    coverage = diversity(manifest)
    save(ROOT/'coverage.json', dict(**coverage, appearance_controls=appearance_invariance()))
    montage()
    lines = ['# 场景多样性资格实验', '',
             '12种子、6因素组、2任务；仿真真值辅助定位/分割。没有模型调用或训练。', '',
             '|组|计划|实际执行|资格不合格|成功|首次成功|物理尝试|',
             '|---|---:|---:|---:|---:|---:|---:|']
    for group, values in result['metrics'].items():
        fields = ['planned','executed','rejected','success','first_success','physical_attempts']
        lines.append('|'+group+'|'+'|'.join(str(values[k]) for k in fields)+'|')
    lines += ['', '## 实际变化范围', '', '```json', json.dumps(coverage,indent=2), '```', '',
              '资格不合格保留在计划分母；几何/可见性合格不保证物理成功。',
              '同一种子的多组和两个任务相关；不声称统计显著或视觉模型能力提升。',
              '容器保持朝向；物体全范围yaw。未新增摩擦/质量/光照/深度噪声。',
              '旧v1保留为静态校验工程失败；无物理执行，不混入本轮绩效分母。',
              '', '![实际场景](scene_grid.jpg)']
    (ROOT/'REPORT.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
