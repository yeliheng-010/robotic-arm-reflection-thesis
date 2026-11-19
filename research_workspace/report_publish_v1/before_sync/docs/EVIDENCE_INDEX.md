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

2026-11-02路径重规划证据位于工作区`scene_pair_route_v1/`：`REPORT.md`、`verification.json`、`manifest.json`、`audit_supplement.json`、`physics/*/attempt_2/route.json`与对应原始执行结果。两个失败各新增一次环境尝试，均规划拒绝且未开始搬运；七个旧成功共享。5806完成11项测试与重建审计，5804/5805审计失败日志保留；没有追加物理重跑。冻结执行清单SHA256：`0466a6adbdc2858241fcfaadccbe942552886647099883574357e25268fbf4f4`。新增成功0，未全量重跑或推广，正式增强仍5/24。

高度解耦/路点与端点剪枝证据位于工作区`scene_pair_route_v2/`：`REPORT.md`、`verification.json`、`endpoint_diagnostic.json`和两个`endpoint_audit_*.json`。5821完成8项测试及144个释放端点独立核验；5807/5812取消日志保留，完整路径穷举未完成、没有新增环境尝试或物理验证。冻结清单SHA256：`b599e0493167fd29a6b34cb170001869af99014ccf5352fde3696fc2cdb26783`。第三次机会未使用，正式增强仍5/24。

最新箱内合法目标与路径证据位于工作区`scene_pair_route_v3/`：`REPORT.md`、`REVIEW.md`、`verification_v2.json`、`manifest.json`、`audit_revision_manifest.json`、`physics/*/result.json`、`route.json`、`guard.json`和`attempt_3/result.json`。5836新增两次第三尝试，961104真实成功、961103抬升掉落，七个旧成功共享；三次预算均已用完。5840严格相等审计失败日志、5849几何差异及本地红绿测试记录均保留；5850的13项测试和最终审计通过。执行manifest SHA256：`f9c4f178756ce13a4c3703530d71930feb2c154729caab5861ce09b9d70fc829`，审计修订清单SHA256：`6d698ff3265f8bbcb6907b7c530c4c5aefe08ebf2ee7552ef5fc0a5abf2917f3`。`LOCAL_EVIDENCE_SHA256.json`列出19个逐字节同步文件，`delivery_verification.json`记录本地交付核对。完整预检候选/接触/图像保留服务器，未全部下载；正式增强仍5/24，未全量重跑或推广。

## 4. 完整产物位置与复现前提

AI自主诊断方向调整的本地证据位于工作区`ai_diagnosis_v1/`：`AUDIT.md`逐项追踪当前规则入口、理想标签、候选/quality和合成补看的来源；`PROTOCOL.md`固定观测/决策/评估边界及下一阶段门禁。`green-final.log`记录18项离线测试，`OFFLINE_VERIFICATION.json`记录21份主要源文件身份不变及两条耗尽账本的STOP-only样例，`examples/`没有模型回复。模型/物理/训练调用均0；当前不证明AI能诊断或恢复，未发布到服务器或替换默认入口。

原服务器实验根目录为 `/home/yeliheng/grasp_server/`，早期pilot位于其 `stability_20261019/`。近期独立目录：

- `candidate_sft_v2/`、`set_sft_v1/`、`set_closed_loop_v2/`。
- `observation_model_control_v1/`、`selector_analysis_v1/`。
- `active_observation_pilot_v1/`、`active_observation_model_v2/`。
- `observation_decision_diagnostic_v2/`。

完整复现需要对应版本源码、manifest、输入/轨迹、基础权重、adapter、提示、依赖和Slurm资源。先核对冻结身份、协议与环境；新实验另建版本，不覆盖历史失败、原始数据或权重。

本仓库没有提供一条命令复现全部实验的承诺，也不发布服务器登录信息、会话凭证或模型服务令牌。
