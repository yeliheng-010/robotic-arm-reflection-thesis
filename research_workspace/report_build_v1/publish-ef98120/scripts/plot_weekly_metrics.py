"""读取冻结实测数据绘图，不拟合平滑曲线，不增加模拟观测。"""
import csv
import numpy as np
from weekly_figure_style import (plt, OUT, DATA_DIR, COLORS, LABELS,
                                 frame, title, finish, load_data)

D = load_data()


def canvas(heading, subtitle):
    fig, ax = plt.subplots(figsize=(10, 5.5))
    fig.subplots_adjust(left=.10, right=.94, bottom=.17, top=.79)
    title(fig, heading, subtitle)
    return fig, ax


def write_csv(name, rows):
    path = DATA_DIR / (name + ".csv")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def training():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), sharey=True)
    fig.subplots_adjust(left=.08, right=.96, bottom=.18, top=.76, wspace=.20)
    title(fig, "微调训练 loss：完整更新记录", "两个版本均为1 epoch；每步对应不同批次，不能当作同批数据反复测量")
    rows = []
    for ax, key, label, color in zip(axes, ("sft159", "sft189"),
                                     ("a  单成功动作 / 159输入", "b  多成功动作 / 189输入"),
                                     (COLORS["previous159"], COLORS["new189"])):
        updates = D["training"][key]
        x, y = [r["step"] for r in updates], [r["loss"] for r in updates]
        assert all(v > 0 for v in y)
        ax.plot(x, y, "o-", color=color, markersize=4, linewidth=2)
        ax.set(yscale="log", title=label, xticks=[1, 5, 10, 15, 20] + ([24] if len(x)==24 else []))
        frame(ax, xlabel="优化器更新步数", ylabel="答案监督 loss（对数坐标）")
        rows += [{"version": key, "step": a, "loss": b} for a, b in zip(x, y)]
    write_csv("training_loss", rows)
    finish(fig, "training_loss", note="所有20/24步均展示，无平滑。两版监督聚合不同，曲线高低不构成受控优劣比较。")


def validation():
    fig, ax = canvas("验证 loss 下降，但不等于任务准确率提高", "159条训练版本；仅训练前后两个检查点，没有虚构中间验证轨迹")
    rows = []
    for group, label, color, shift in (("dev", "开发诊断 n=49", COLORS["base"], .01),
                                      ("legacy_dev", "旧场景诊断 n=29", COLORS["new189"], -.01)):
        y = [D["validation"][phase][group]["loss"] for phase in ("before", "after")]
        ax.plot([0, 1], y, "o-", label=label, color=color, linewidth=2.4, markersize=7)
        rows += [{"subset": group, "checkpoint": p, "loss": v} for p, v in zip(("before", "after"), y)]
    ax.set(xticks=[0, 1], xticklabels=["微调前", "微调后"], xlim=(-.16, 1.16), yscale="log")
    frame(ax, xlabel="模型检查点", ylabel="答案 token 交叉熵（对数坐标）")
    ax.legend(loc="upper right")
    write_csv("validation_loss", rows)
    finish(fig, "validation_loss", note="筛选后的开发子集；非最终测试。物理效果须看完整闭环任务，不能由loss替代。")


def sft_success():
    fig, ax = canvas("微调闭环：增益有限，规则仍是强基线", "同一60个开发条件 × 4方法；最多3次尝试；共享6个批次内种子组")
    rows = D["closed_loop"]
    values = [r["successes"] / r["executed"] * 100 for r in rows]
    bars = ax.bar(range(len(rows)), values, width=.58, color=[COLORS[r["method"]] for r in rows])
    for bar, row in zip(bars, rows):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+2,
                f'{row["successes"]}/60', ha="center", fontsize=12)
    ax.set(ylim=(0, 110), yticks=range(0, 101, 20),
           xticks=range(len(rows)), xticklabels=[LABELS[r["method"]] for r in rows])
    frame(ax, xlabel="方法", ylabel="任务成功率（%）")
    write_csv("sft_success", [{"method": r["method"], "success": r["successes"], "n": r["executed"]} for r in rows])
    finish(fig, "sft_success", note="原始总体比例，无置信区间/显著性主张；数据量、监督目标与步数未独立控制。")


def aggregation():
    fig, ax = canvas("含噪反馈：中位数聚合优于只取最新测量", "24条件 / 12种子组；每种聚合下，规则与基础模型的成功数相同")
    rows = D["aggregation"]
    exported = []
    for key, label, color, marker in (("rule_latest", "最新测量（规则=模型）", COLORS["rule"], "s"),
                                       ("rule_median", "中位数（规则=模型）", COLORS["adaptive"], "o")):
        counts = [r["methods"][key]["successes"] for r in rows]
        x = [r["budget"] for r in rows]
        ax.plot(x, np.array(counts)/24*100, marker=marker, label=label, color=color, linewidth=2.6)
        exported += [{"method": key, "budget": a, "success": b, "n": 24} for a,b in zip(x, counts)]
    ax.set(xticks=[1, 2, 3], ylim=(0, 108), yticks=range(0, 101, 20))
    frame(ax, xlabel="最大物理执行预算", ylabel="任务成功率（%）")
    ax.legend(loc="lower right")
    write_csv("aggregation_budget", exported)
    finish(fig, "aggregation_budget", note="共享前缀的冻结预算实验；相同聚合下选择器没有成功率差异，不归为模型独立收益。")


def active():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4))
    fig.subplots_adjust(left=.08, right=.97, bottom=.20, top=.76, wspace=.24)
    title(fig, "主动观测：效果与观测费用同时报告", "24条件 / 6种子组；固定三次执行预算、最多两次额外观测")
    methods = D["active"]["overall"]["methods"]
    for key, label, marker in (("fixed_first","固定首次观测","s"), ("adaptive","自适应规则","o"),
                               ("base_current","基础4B / +历史（相同）","^")):
        y = methods[key]["cumulative_success"]
        axes[0].plot([1,2,3], np.array(y)/24*100, label=label, color=COLORS[key],
                     marker=marker, linewidth=2.4)
    axes[0].set(title="a  随实际尝试累计的成功率", xticks=[1,2,3], ylim=(0, 85))
    frame(axes[0], xlabel="已允许的累计尝试次数", ylabel="累计任务成功率（%）")
    axes[0].legend(loc="upper left", fontsize=9)
    keys = list(methods)
    axes[1].bar(range(4), [methods[k]["extra_observations"] for k in keys],
                color=[COLORS[k] for k in keys], width=.58)
    for i,k in enumerate(keys):
        axes[1].text(i, methods[k]["extra_observations"]+1.5, str(methods[k]["extra_observations"]), ha="center")
    axes[1].set(title="b  全批次实际追加观测", xticks=range(4),
                xticklabels=["固定","自适应","基础4B","+历史"], ylim=(0,56))
    frame(axes[1], xlabel="方法", ylabel="额外观测总次数")
    finish(fig, "active_observation", note="左图是同一三次预算策略的累计成功，非独立预算反事实；比例不表示统计显著。")


def observation_value():
    fig, ax = canvas("固定缺测快照：补充观测提高下一次重试成功数", "11快照 / 10条件 / 5种子组；固定观测后，按原场景种子重置并重试一次")
    arms = D["diagnostic"]["overall"]["arms"]
    exported = []
    for method, label, color, marker in (("rule","规则",COLORS["rule"],"s"),
                                         ("model","基础4B",COLORS["base"],"o")):
        counts = [arms[f"{method}_l{n}"]["successes"] for n in range(3)]
        ax.plot(range(3), np.array(counts)/11*100, marker=marker, color=color, label=label, linewidth=2.6)
        for x,y in enumerate(counts):
            ax.annotate(f"{y}/11", (x,y/11*100), xytext=(0, 10 if method=="model" else -18),
                        textcoords="offset points", ha="center", color=color)
        exported += [{"selector":method,"observations":n,"success":y,"n":11} for n,y in enumerate(counts)]
    ax.set(xticks=[0,1,2], ylim=(-10,85), yticks=range(0,81,20))
    frame(ax, xlabel="固定追加观测次数", ylabel="下一次重试成功率（%）")
    ax.legend(loc="upper left")
    write_csv("observation_value", exported)
    finish(fig, "observation_value", note="66分支均实际执行。非恢复失败瞬间、非三次自主闭环、非独立泛化测试。")


def noise():
    fig, axes = plt.subplots(1,2,figsize=(12,5.5))
    fig.subplots_adjust(left=.09, right=.96, bottom=.20, top=.75, wspace=.25)
    title(fig, "噪声作用于反馈残差，而不是给图片加模糊", "离线预检：4条真实失败反馈 × 6配置 × 3投影种子 = 72次投影")
    profiles = sorted({(r["sigma_m"],r["missing_probability"]) for r in D["noise"]})
    for sigma, color, marker in ((0, COLORS["rule"], "s"),(.005,COLORS["base"],"o"),(.015,COLORS["new189"],"^")):
        rows=[r for r in D["noise"] if r["sigma_m"]==sigma and not r["missing"]]
        values=np.array([r["delta_m"] for r in rows])*1000
        axes[0].scatter(values[:,0],values[:,1],s=35,alpha=.65,color=color,marker=marker,label=f"σ={sigma*1000:g} mm")
    axes[0].axhline(0,color="#cad3dc",lw=.6)
    axes[0].axvline(0,color="#cad3dc",lw=.6)
    axes[0].set(title="a  非缺失字段的实际噪声增量", xlim=(-45,45), ylim=(-45,45))
    frame(axes[0],xlabel="X残差增量（mm）",ylabel="Y残差增量（mm）")
    axes[0].legend(loc="upper left",fontsize=9)
    counts=[sum(r["missing"] for r in D["noise"] if (r["sigma_m"],r["missing_probability"])==p) for p in profiles]
    axes[1].bar(range(6),counts,color=COLORS["rule"],width=.6)
    for i,y in enumerate(counts):
        axes[1].text(i,y+.12,str(y),ha="center")
    axes[1].set(title="b  缺失字段次数（全部记录）",xticks=range(6),
                xticklabels=[f"{s*1000:g}\n{p:g}" for s,p in profiles],ylim=(0,max(counts)+1))
    frame(axes[1],xlabel="上行：σ（mm）   下行：缺失概率",ylabel="实际缺失字段数")
    finish(fig,"feedback_noise",note="3σ截断高斯；缺失不补零。点可能重叠；这些投影不是72个独立物理任务。")


if __name__ == "__main__":
    for function in (training, validation, sft_success, aggregation, active, observation_value, noise):
        function()
    print("Rendered 7 data figures.")
