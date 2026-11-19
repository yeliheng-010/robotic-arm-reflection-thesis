"""组合真实截图；标记仅来自模型预测和SAM输出。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
SIZE, MARGIN, HEADER = 520, 20, 42


def main():
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 22)
    small = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    image = Image.new('RGB', (1100, 1260), '#f4f6fa')
    draw = ImageDraw.Draw(image)
    draw.text((20, 16), '冻结随机布局：模型自主定位 → SAM分割', font=font, fill='#15253d')
    for column, seed in enumerate((978501, 978505)):
        for row, name in enumerate(('grounding_audit.png', 'mask_overlay.png')):
            path = (ROOT/f'evidence/images/{seed}/{name}' if row == 0
                    else ROOT/f'evidence/images/sam/{seed}/{name}')
            panel = Image.open(path).convert('RGB').resize((SIZE, SIZE))
            x, y = MARGIN+column*(SIZE+MARGIN), 62+row*(SIZE+HEADER+MARGIN)
            label = f'{seed}  '+('模型定位（十字为预测点）' if row == 0 else 'SAM分割（绿色为预测掩码）')
            draw.text((x, y), label, font=small, fill='#15253d')
            image.paste(panel, (x, y+HEADER))
    draw.text((20, 1228), '真实仿真截图；本轮尚未执行抓放，图中结果不代表任务成功。', font=small, fill='#4a5669')
    image.save(ROOT/'evidence/model_perception_contact_sheet.png')


if __name__ == '__main__':
    main()
