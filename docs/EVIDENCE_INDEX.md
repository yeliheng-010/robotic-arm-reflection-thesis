# 证据与复现索引

更新：2026-10-28。仓库公开精选审计证据，不包含完整仿真系统、模型权重和全部原始轨迹。可据此核对报告数字及证据身份；仅克隆仓库不能复现实验全流程。

## 1. 本轮新增证据

新增可视化见[图表说明](FIGURE_GALLERY.md)。[绘图数据](../evidence/figures_20261028/source_data.json)保存9个服务器来源文件的hash、完整绘图数值和10张截图身份；[图包hash清单](../evidence/figures_20261028/SHA256SUMS.txt)核对公开图片、数据与脚本。场景原图来自10月25日，图包更新于10月28日。

| 文件 | 内容与边界 |
|---|---|
| [已完成研究摘要](../evidence/20261028/completed_studies.json) | 本次从服务器读取6个已完成研究的verification.json，提取训练、成功率、调用、成本及审计字段；另含选择器只读分析 |
| [诊断运行中快照](../evidence/20261028/diagnostic_snapshot.json) | 23:10时仍在batch，彼时最终审计缺失；保留历史不覆盖 |
| [诊断最终完成摘录](../evidence/20261028/diagnostic_completed.json) | 23:19读取最终状态，402任务请求、66分支/执行、成功与费用及全阶段审计 |
| [本轮文件SHA256](../evidence/20261028/SHA256SUMS.txt) | 上述公开摘录文件的字节身份，不包含本文件自身 |

摘要的 `source` 为服务器实验根目录下的相对产物名；`source_sha256` 对应完整源文件UTF-8内容。摘录去掉逐轨迹明细、部分细分分析和内部代码路径，因此不能拿摘录文件哈希与源文件哈希直接比较。

本次只读核对已有审计产物，**没有重跑原实验或对全部原始轨迹重新审计**。每个研究的 `passed` 是对应审计产物记录的结果，不意味着真实机械臂迁移或论文结论已获验证。

## 2. 当前结论与来源映射

| 主张 | 实验 / 源字段 |
|---|---|
| 159条、20次更新、496张量变化、三次重载误差0 | `candidate_sft_v2 / training, after` |
| 189输入、197回复、24次更新 | `set_sft_v1 / training` |
| 60条件规则57、base55、两SFT56 | `set_closed_loop_v2 / metrics[field=all], paired` |
| 三次预算下最新值22/24、中位数24/24，模型与规则一致 | `observation_model_control_v1 / budget_analysis.curves` |
| 45次同输入、同选择、唯一测量候选；仅36次下一步成功 | `selector_analysis / fields.totals` |
| 规则pilot15/24与16/24、观测46与42 | `active_observation_pilot_v1 / budget_analysis.curves` |
| 最新四组14/17/14/14，210次唯一执行、82任务调用 | `active_observation_model_v2 / analysis.overall, physical_executions, ledger` |
| 模型诊断402完成、各变体OBSERVE计数、费用读取39/41 | 诊断快照 `model_progress.json, model_verification.json` |
| 11快照0/1/2次观测，规则0/5/6、模型1/6/7 | 最终完成摘录 `verification.json / analysis.overall.arms` |
| 最终完成与篡改拒绝 | 最终完成摘录 `STATUS.json, verification.json` |

`expected` 的单位取决于研究：主动观测为条件数，60条件四组闭环为方法轨迹数。训练审计的 `physics_evaluated=false` 是当时训练阶段状态；后续物理评估有独立证据，不回写旧文件。

## 3. 历史证据（2026-10-21）

以下仅说明历史状态，不再作为当前采集或资源安排：

- [21:54采集快照](../evidence/status_20261021_215414.json)、[服务器检查](../evidence/server_check_20261021_215414.txt)：当时1099任务及474/139/110样本计数。
- [首版快照](../evidence/status_snapshot.json)、[首版服务器检查](../evidence/server_check.txt)：更早时间点，不能与后续训练样本数混用。
- [实现检查清单](../evidence/implementation_review.json)：当时README所引用模块的检查记录。
- [pilot训练结果](../evidence/pilot/result.json)、[manifest](../evidence/pilot/manifest.json)：163样本、21更新的早期参数修正模型。
- [验证生成](../evidence/pilot/validation_generation.json)、[训练更新](../evidence/pilot/updates.jsonl)：标签与训练记录，不等于物理成功率。
- [早期闭环结果](../evidence/closed_loop/result.json)、[交付审计](../evidence/closed_loop/delivery_verification.json)：6条件、4方法的历史pilot。
- [历史失败](../evidence/closed_loop/failure.json)、[恢复记录](../evidence/closed_loop/completion_recovery.json)：保留工程失败与恢复。
- [历史证据SHA256](../evidence/SHA256SUMS.txt)：原有证据与图片清单；本轮新增文件使用上方独立清单。

旧版README及计划保存在 [4113c24](https://github.com/yeliheng-010/robotic-arm-reflection-thesis/tree/4113c24)。早期163条、后续159条与189输入版本的任务和监督口径不同，不作简单累加。

## 4. 完整产物位置与复现前提

原服务器实验根目录为 `/home/yeliheng/grasp_server/`，早期pilot位于其 `stability_20261019/`。近期独立目录：

- `candidate_sft_v2/`、`set_sft_v1/`、`set_closed_loop_v2/`。
- `observation_model_control_v1/`、`selector_analysis_v1/`。
- `active_observation_pilot_v1/`、`active_observation_model_v2/`。
- `observation_decision_diagnostic_v2/`。

完整复现需要对应版本源码、manifest、输入/轨迹、基础权重、adapter、提示、依赖和Slurm资源。先核对冻结身份、协议与环境；新实验另建版本，不覆盖历史失败、原始数据或权重。

本仓库没有提供一条命令复现全部实验的承诺，也不发布服务器登录信息、会话凭证或模型服务令牌。
