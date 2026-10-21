# 证据与复现索引

本仓库提供精选审计材料，不包含完整仿真系统、全部训练数据、权重或每个任务的原始轨迹。因此可以复核本报告的关键数字与证据身份，但仅克隆本仓库不能重新运行全部实验。

## 1. 当前状态

- [2026-10-21 21:54采集快照](../evidence/status_20261021_215414.json)：README本轮更新采用的1099任务、474/139/110样本记录。
- [21:54服务器检查](../evidence/server_check_20261021_215414.txt)：3718双卡运行状态与当时队列、显存。
- [README实现检查清单](../evidence/implementation_review.json)：本轮只读核对的本地模块及hash，不等于重新验证所有远端运行源码。

- [首版19:49采集状态快照](../evidence/status_snapshot.json)：保留当时采集时间、来源路径和原始status字段。
- [首版服务器只读检查](../evidence/server_check.txt)：GPU、Slurm队列及3712/3714/3717/3718状态；记录运行中作业的0:0不等于最终成功。

## 2. 初步训练与生成

- [result.json](../evidence/pilot/result.json)：真实更新、验证loss、adapter变化、保存重载检查等。
- [manifest.json](../evidence/pilot/manifest.json)：基础模型、数据身份、训练参数与源码/模型hash。
- [validation_generation.json](../evidence/pilot/validation_generation.json)：保存后独立生成的48条验证记录。
- [before.json](../evidence/pilot/before.json)、[after.json](../evidence/pilot/after.json)：预固定开发例的生成，不是全部48条基线对照。
- [updates.jsonl](../evidence/pilot/updates.jsonl)：逐次训练更新。
- [completion_verification.json](../evidence/pilot/completion_verification.json)、[final_integrity.json](../evidence/pilot/final_integrity.json)：归档验证记录。

训练result的`physics_evaluated=false`反映训练完成时状态。后续物理闭环证据另见closed_loop目录，不改写历史文件以掩盖阶段差异。

## 3. 仿真闭环

- [result.json](../evidence/closed_loop/result.json)：四组汇总、逐场景结果与恢复说明。
- [delivery_verification.json](../evidence/closed_loop/delivery_verification.json)：24任务、6配对场景、13次模型调用的审计结果。
- [failure.json](../evidence/closed_loop/failure.json)：保留原汇总异常。
- [completion_recovery.json](../evidence/closed_loop/completion_recovery.json)：两项汇总恢复、原始结果hash、恢复代码身份。
- [source-snapshot.json](../evidence/closed_loop/source-snapshot.json)：冻结代码身份记录，不是全部源码。
- [jobs.tsv](../evidence/closed_loop/jobs.tsv)：原作业最终状态。
- [仿真截图](../assets/case_01_comparison.png)：案例说明，不替代全量表。

上述历史证据从本地已归档文件逐字节复制；本轮另实时核对作业状态和当前采集。不是本轮重新跑训练或重新做全部轨迹审计。

## 4. 完整产物位置

服务器实验根目录：`/home/yeliheng/grasp_server/stability_20261019/`。

| 内容 | 相对实验根目录 |
|---|---|
| 初步冻结数据 | `pilot_sft_data_v1/` |
| 模型adapter与训练记录 | `pilot_sft_v1/` |
| 开发闭环全部任务轨迹 | `closed_loop_v1/tasks/` |
| 闭环完整冻结manifest及请求 | `closed_loop_v1/manifest.json`、`service_requests.jsonl` |
| 当前采集 | `expert_batch_v1/` |
| 当前调度控制 | `expert_dual_after_loop_deploy_v1/` |

基础模型：`/home/yeliheng/grasp_server/qwen35/models/Qwen3.5-4B`。运行模型需基础权重、tokenizer、adapter、提示模板和对应环境，不能只复制adapter就视为完整模型。

运行源码分别位于原项目与独立实验包。复现前读取原环境RUNBOOK、TRAINING_PROTOCOL及冻结manifest，核对依赖与模型hash。新的闭环运行须新冻结版本并整合安全汇总，不能直接重用此次一次性恢复入口。

## 5. 仓库文件身份与更新规则

[SHA256SUMS.txt](../evidence/SHA256SUMS.txt)记录上传的证据文件与图片身份，不包含自身；版本控制负责文档变更。未来状态更新需新增带时间戳的快照或明确版本，不能将新样本计数写成旧训练数据规模。

更新主结果时须同时更新README、CURRENT_PROGRESS和证据索引，标明是开发、验证还是最终测试。负结果、异常与恢复日志不得删除以改善表观成绩。
