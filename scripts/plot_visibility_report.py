"""从公开CSV重建三张可见性标定图；无需原始仿真环境。"""
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "evidence/visibility_6495_6497"
OUT = REPO / "assets/visibility_6495_6497"
BLUE, GRAY, ORANGE = "#2878A5", "#87949C", "#C15A27"
SIZE = (180 / 25.4, 112 / 25.4)
FOOTNOTE = "1个开发布局 · 同一释放前快照 · 噪声技术重复 · 非完整任务成功率"


def configure():
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
                         "font.size": 8, "axes.titlesize": 11, "axes.labelsize": 9,
                         "pdf.fonttype": 42, "svg.fonttype": "none", "axes.unicode_minus": False,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.linewidth": 0.7, "legend.frameon": False})
    OUT.mkdir(parents=True, exist_ok=True)


def canvas(title):
    fig, ax = plt.subplots(figsize=SIZE)
    fig.subplots_adjust(left=0.12, right=0.97, bottom=0.23, top=0.81)
    fig.text(0.12, 0.93, title, fontsize=11, weight="bold")
    fig.text(0.12, 0.055, FOOTNOTE, fontsize=7, color="#475569")
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#E4E8EC", linewidth=0.5)
    return fig, ax


def save(fig, name):
    # 单面板，无可比较面板；对齐门禁记为不适用。
    fig.savefig(OUT / f"{name}.png", dpi=300)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.svg")
    svg = OUT / f"{name}.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines()) + "\n",
                   encoding="utf-8", newline="\n")
    plt.close(fig)


def color_rows(rows):
    return [ORANGE if int(row["accurate"]) == 0 else
            BLUE if row["experiment"].endswith("v2") else GRAY for row in rows]


def accuracy_plot(rows):
    fig, ax = canvas("可见比例增加，并不保证位姿估计更准确")
    ax.grid(False)
    values = [100 * int(r["accurate"]) / int(r["noise_repeats"]) for r in rows]
    bars = ax.bar(range(len(rows)), values, color=color_rows(rows), width=0.62)
    labels = [f'{r["accurate"]}/{r["noise_repeats"]}' for r in rows]
    ax.bar_label(bars, labels=labels, padding=4, fontsize=7)
    ax.set_ylim(0, 116)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_ylabel("位姿估计准确率（%）")
    ax.set_xticks(range(len(rows)), [f'{float(r["visibility"])*100:.2f}' for r in rows], rotation=40)
    ax.set_xlabel("实际目标可见比例（%，每个位置对应一个视角）")
    fig.text(0.12, 0.85, "准确：中心误差≤10 mm且长轴角误差≤12°；柱上为准确次数/噪声重复数", fontsize=7)
    save(fig, "visibility_accuracy")


def error_plot(rows, measurements):
    fig, ax = canvas("77.34%视角出现中心估计退化")
    groups = [[float(m["center_error_mm"]) for m in measurements
               if m["experiment"] == r["experiment"]
               and abs(float(m["visibility"]) - float(r["visibility"])) < 1e-12] for r in rows]
    ax.boxplot(groups, positions=range(len(rows)), widths=0.48, showfliers=False,
               medianprops={"color": "#111827"}, boxprops={"color": GRAY},
               whiskerprops={"color": GRAY}, capprops={"color": GRAY})
    rng = np.random.default_rng(6497)
    for index, (values, color) in enumerate(zip(groups, color_rows(rows))):
        ax.scatter(index + rng.uniform(-0.16, 0.16, len(values)), values, s=8,
                   color=color, alpha=0.65, linewidths=0)
    ax.axhline(10, color="#44546A", linestyle="--", linewidth=0.8)
    ax.set_ylim(0, 75)
    ax.set_ylabel("中心误差（mm）")
    ax.set_xticks(range(len(rows)), [f'{float(r["visibility"])*100:.2f}' for r in rows], rotation=40)
    ax.set_xlabel("实际目标可见比例（%）")
    fig.text(0.12, 0.85, "全部192次测量均展示；虚线为10 mm评估容限；准确判定还需长轴角误差合格", fontsize=7)
    save(fig, "center_error_distribution")


def quality_plot(measurements):
    fig, ax = canvas("质量检查拦住退化估计，同时减少可用样本")
    rows = [r for r in measurements if r["experiment"].endswith("v2")]
    combinations = [(1, 1), (1, 0), (0, 1), (0, 0)]
    counts = [sum(int(r["quality_passed"]) == q and int(r["accurate"]) == a for r in rows)
              for q, a in combinations]
    assert counts == [97, 0, 1, 22] and len(rows) == 120
    bars = ax.bar(range(4), counts, color=[BLUE, ORANGE, GRAY, ORANGE], width=0.56)
    ax.bar_label(bars, labels=[str(v) for v in counts], padding=5, fontsize=9)
    ax.set_xticks(range(4), ["接受且准确", "接受但不准", "拒绝但准确", "拒绝且不准"])
    ax.set_ylabel("估计次数")
    ax.set_ylim(0, 114)
    ax.set_xlabel("高区间6个视角 × 每视角20次噪声重复")
    fig.text(0.12, 0.85, "接受率97/120（80.8%）；已接受样本准确97/97；全样本准确98/120", fontsize=7)
    save(fig, "quality_gate_outcomes")


def main():
    configure()
    with (DATA / "summary.csv").open(encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    with (DATA / "measurements.csv").open(encoding="utf-8") as stream:
        measurements = list(csv.DictReader(stream))
    assert len(rows) == 12 and len(measurements) == 192
    accuracy_plot(rows)
    error_plot(rows, measurements)
    quality_plot(measurements)
    print("Exported 3 figures in PNG/PDF/SVG.")


if __name__ == "__main__":
    main()
