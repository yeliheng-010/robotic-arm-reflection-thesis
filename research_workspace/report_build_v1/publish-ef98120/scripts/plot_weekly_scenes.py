"""组合真实仿真截图；不生成新场景，不改动截图内容。"""
from PIL import Image
from weekly_figure_style import plt, DATA_DIR, title, finish, load_data

D = load_data()
SCENE_TITLES = (
    "a  无挡板控制（同1cm布局）", "b  物体位置 ±1cm",
    "c  物体位置 ±3cm", "d  物体朝向 ±30°",
    "e  位置 ±2cm + 朝向 ±20°", "f  容器位置 ±1cm")
METHOD_NAMES = ("固定首次观测", "自适应规则", "基础4B", "基础4B+历史")


def scene_plate():
    fig, axes = plt.subplots(2,3,figsize=(12,9.8))
    fig.subplots_adjust(left=.04,right=.96,bottom=.08,top=.86,wspace=.06,hspace=.14)
    title(fig, "场景扩展：真实仿真截图", "10月25日记录 · 种子910001 · RedBlock → BlueBin · 五种扰动 + 无挡板控制")
    for ax, row, label in zip(axes.flat,D["scene_images"],SCENE_TITLES):
        ax.imshow(Image.open(DATA_DIR/"raw"/row["file"]))
        ax.axis("off")
        ax.set_title(label,fontsize=12,pad=7)
    finish(fig,"scene_variants",note="原始before截图完整保留，仅统一缩放排版。标注为采样范围，不是每个物体的实际偏移量。")


def recovery_plate():
    fig, axes = plt.subplots(1,4,figsize=(14,5.1))
    fig.subplots_adjust(left=.03,right=.97,bottom=.12,top=.78,wspace=.06)
    title(fig,"同一复合故障：四种策略的最终状态","PurpleCapsule → RedBin · M1_940301_grasp_place · 第3次尝试结束后")
    for i,(ax,row,label) in enumerate(zip(axes,D["recovery_images"],METHOD_NAMES)):
        ax.imshow(Image.open(DATA_DIR/"raw"/row["file"]))
        ax.axis("off")
        outcome = "成功" if row["success"] else "失败"
        ax.set_title(f"{chr(97+i)}  {label}\n物理验收：{outcome}",fontsize=11,pad=9)
    finish(fig,"recovery_case",note="特意展示一个已报告差异案例解释机制；不是随机代表样本。完整总体结果为14/17/14/14（分母24）。")


if __name__ == "__main__":
    scene_plate()
    recovery_plate()
    print("Rendered 2 scene plates.")
