"""图形样式与导出；所有数值均由source_data.json提供。"""
import json
import os
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "evidence" / "figures_20261028"
OUT = ROOT / "assets" / "weekly_20261028"
QA = ROOT / "figure_qa"
DPI = 300
COLORS = {"rule": "#697586", "fixed_first": "#697586", "adaptive": "#087f8c",
          "base": "#3566b0", "base_current": "#3566b0", "base_history": "#8660a8",
          "previous159": "#d18039", "new189": "#8660a8"}
LABELS = {"rule": "规则", "fixed_first": "固定首次观测", "adaptive": "自适应规则",
          "base": "基础4B", "base_current": "基础4B", "base_history": "基础4B+历史",
          "previous159": "微调159", "new189": "微调189"}

FONT = "Noto Sans CJK SC"
plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": [FONT, "DejaVu Sans"],
                     "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "pdf.fonttype": 42, "svg.fonttype": "none",
                     "axes.unicode_minus": False, "legend.frameon": False,
                     "figure.facecolor": "white"})
OUT.mkdir(parents=True, exist_ok=True)
QA.mkdir(parents=True, exist_ok=True)


def load_data():
    return json.loads((DATA_DIR / "source_data.json").read_text())


def frame(ax, *, xlabel, ylabel):
    ax.set(xlabel=xlabel, ylabel=ylabel)
    ax.grid(axis="y", color="#d9e0e7", linewidth=.7, alpha=.65)
    ax.set_axisbelow(True)


def title(fig, heading, subtitle):
    fig.suptitle(heading, x=.06, y=.97, ha="left", fontsize=18, fontweight="bold")
    fig.text(.06, .90, subtitle, ha="left", fontsize=10, color="#536273")


def finish(fig, name, *, note):
    fig.text(.06, .025, note, ha="left", va="bottom", fontsize=9, color="#536273")
    fig.canvas.draw()
    qa_path = os.environ.get("FIGURE_QA_PATH")
    if qa_path:
        sys.path.insert(0, qa_path)
        from audit_panel_alignment import require_matplotlib_panel_alignment
        require_matplotlib_panel_alignment(fig, json_out=QA / f"{name}.alignment.json",
                                           tolerance_pt=1.5, strict=True)
    else:
        (QA / f"{name}.alignment.json").write_text(
            '{"status":"NOT AUDITABLE","reason":"set FIGURE_QA_PATH to audit tools"}\n')
    fig.savefig(OUT / f"{name}.png", dpi=DPI, facecolor="white")
    fig.savefig(OUT / f"{name}.pdf", facecolor="white")
    fig.savefig(OUT / f"{name}.svg", facecolor="white")
    svg = OUT / f"{name}.svg"
    text = "\n".join(line.rstrip() for line in svg.read_text(encoding="utf-8").splitlines())
    svg.write_text(text + "\n", encoding="utf-8", newline="\n")
    plt.close(fig)
