"""从已保存RGB生成证据对照图；右图明确标注非物理执行。"""
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from qualified_model_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def decode(data):
    first = np.asarray(data['first'], dtype=np.int32)
    remaining = first + np.cumsum(data['deltas'], axis=0, dtype=np.int32)
    values = np.concatenate([first[None], remaining], axis=0)
    assert np.all((values >= 0) & (values <= 255))
    return values.astype(np.uint8)


def main():
    evidence = ROOT/'evidence'
    with np.load(evidence/'predicted_held_rgb.npz') as data:
        frames = decode(data)
    report = read(evidence/'remote/run/predicted_held/qualification.json')
    actual_hash = hashlib.sha256(frames[-1].tobytes()).hexdigest()
    assert actual_hash == report['rgb']['post']['after_sha256']
    first = Image.open(PROJECT/'qualified_task_v1/evidence/images/audit/978505/qualified.png').convert('RGB')
    after = Image.fromarray(frames[-1])
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)
    canvas = Image.new('RGB', (1320, 850), '#f5f6f8')
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 12), '布局978505：模型方案通过静态路径；持物观察尚未合格', font=font, fill='#162333')
    draw.text((20, 55), '已合格初态：真实仿真观测', font=small, fill='#125447')
    draw.text((680, 55), '理想刚性持物快照：预测图，未执行抓取', font=small, fill='#a33721')
    canvas.paste(first.resize((640, 640)), (20, 90))
    canvas.paste(after.resize((640, 640)), (680, 90))
    draw.text((20, 747), '抓姿由模型选择：long_positive / 20mm / 倾角15° / 方位角90° / 对称角0°', font=small, fill='#162333')
    draw.text((20, 778), '预测可见比例：胶囊41.7%，托盘73.0%，锤子0%；原全14门禁拒绝，未用作模型或训练输入。', font=small, fill='#a33721')
    draw.text((20, 809), '相机与阈值未变。本图不代表实际夹持、任务成功或模型识别结果。', font=small, fill='#485463')
    path = evidence/'initial_vs_predicted_held.png'
    with path.open('xb') as stream:
        canvas.save(stream, format='PNG')
    save(evidence/'FIGURE_PROVENANCE.json', dict(figure_sha256=sha(path),
        predicted_rgb_sha256=actual_hash, physical_attempts=0, frames=len(frames)))
    print(path)


if __name__ == '__main__':
    main()
