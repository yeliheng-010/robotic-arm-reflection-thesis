"""只解码已保存RGB，制作真实执行前后对照；不产生新仿真状态。"""
from pathlib import Path
import hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from qualified_model_v1.common import read, save, sha
from qualified_entry_v1.figure import decode

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT/'evidence'


def original(phase):
    folder = EVIDENCE/'remote/run/physical'/phase
    with np.load(folder/'rgb_0.npz') as data:
        frames = decode(data)
    digest = hashlib.sha256(frames[-1].tobytes()).hexdigest()
    assert digest == read(folder/'qualification.json')['rgb']['post']['after_sha256']
    image = Image.fromarray(frames[-1])
    path = EVIDENCE/f'{phase}.png'
    with path.open('xb') as stream:
        image.save(stream, format='PNG')
    return image, dict(source=str(folder.relative_to(ROOT)/'rgb_0.npz'),
        decoded_rgb_sha256=digest, png_sha256=sha(path))


def main():
    first, before = original('initial_observation')
    last, after = original('final_observation')
    canvas = Image.new('RGB', (1320, 855), '#f5f6f8')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 19)
    draw.text((20, 12), '978505 单次物理仿真：接近后闭合，夹爪与托盘接触，安全中止', font=font, fill='#162333')
    draw.text((20, 55), '真实执行初态：全14物体观察资格通过', font=small, fill='#125447')
    draw.text((680, 55), '停止后的保存状态：仅供私有诊断', font=small, fill='#a33721')
    canvas.paste(first, (20, 90))
    canvas.paste(last, (680, 90))
    draw.text((20, 747), '独立末态重建：托盘前壁两处接触，穿入约0.390 mm / 0.081 mm；未进入搬运或释放。', font=small, fill='#162333')
    draw.text((20, 780), '末态观察拒绝：胶囊可见1.08%、托盘39.49%、橙球67.12%；未作为模型/控制/训练输入。', font=small, fill='#a33721')
    draw.text((20, 813), '相机与阈值未变；图像来自已保存状态的独立快照，不能用于判断精确接触深度。', font=small, fill='#485463')
    path = EVIDENCE/'initial_vs_stopped.png'
    with path.open('xb') as stream:
        canvas.save(stream, format='PNG')
    save(EVIDENCE/'FIGURE_PROVENANCE.json', dict(initial=before, final=after,
        figure_sha256=sha(path), generator_sha256=sha(ROOT/'figure.py'),
        physical_attempts_added=0, final_image_private_diagnostic_only=True))
    print(path)


if __name__ == '__main__':
    main()
