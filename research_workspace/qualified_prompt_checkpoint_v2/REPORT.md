---
experiment_id: qualified_prompt_checkpoint_v2-978505
date: 2026-11-18
timezone: America/Los_Angeles
status: one_generation_and_independent_audit_complete
actual_generations_across_v1_v2: 1
model_reservations_across_v1_v2: 2
planning_sessions: 0
physical_attempts: 0
training_runs: 0
---

# 末尾拒绝核对后生成了新动作，安全性尚未检查

用户采纳[诊断阶段建议](../qualified_feedback_diagnostic_v1/REPORT.md)，授权最多1次真实模型生成。**实际模型选择了不同于5条历史拒绝记录的新动作，严格JSON有效；完整输入与原始输出经独立审计。** 本轮没有规划、物理执行或训练，不能将新颖动作称为安全方案或抓放成功。

|项目|本轮事实|
|---|---|
|模型|Qwen3.5-4B基础模型，adapter_enabled=false|
|动作|PROPOSE_GRASP|
|region / depth_mm|center / 15|
|tilt_deg / azimuth_deg / symmetry_deg|30 / 135 / 180|
|输入/输出|10725 / 48 token，EOS结束，严格JSON有效|
|历史重复|没有重复任何已拒绝完整参数组合|
|结果分类|novel_action_unchecked；ready=false，safety_evaluated=false|
|实际生成预算|原授权1次，累计消耗1次，余量0|

模型动作是原始输出，不是程序从候选池代选。没有硬性排除解码，没有补抽；该新动作未生成proposal，未检查端点、路径、闭合构型或执行入口。证据见[原始响应](evidence/remote/run/response.json)与[结果](evidence/remote/run/result.json)。

## 请求改动和因果解释边界

使用已保存B草案，在原用户正文末尾追加decision_checkpoint：重复最新公开动作/拒绝阶段，要求逐项比较全部已拒绝参数，自主选另一个白名单动作或STOP。不提供推荐抓姿、碰撞实体、私有几何或诊断原因。原系统、RGB、完整128/256观测点、历史、目标箱几何、白名单、贪心解码/seed42/enable_thinking=false均保持；C“清理上一定位阶段文字”未启用。

同时将请求planning预算1→0，如实描述本轮不规划。相对于旧decision_2，正文变化是checkpoint与规划预算两处；相对于v1失败准备，本次请求逐字节一致。**新动作是一次开发观察，不能归因于checkpoint的单独作用，也不是严格配对或统计改进。** 不重跑旧基线，不据单例宣称模型已普遍掌握反馈反思。

相机、全14/85%观察资格、尺寸/连通性/6mm标定、3mm深度噪声/2%缺失和全部安全门槛保持。复用合格初态RGB，未提供旧失败末态不合格图。

## 生成前工程中止及隔离恢复

[v1失败记录](../qualified_prompt_checkpoint_v1/REPORT.md)完整保留：6811已加载模型并保存输入，但把PyTorch虚拟命名空间的类属性`_classes.py`当作真实项目文件，来源核验拒绝，generate调用0次。6812第一次CPU审计对属性位置的假设错误，失败也保留；6814修正审计确认零生成、输入张量一致及工程根因。

v1按原协议停止，claim=1不删除，不覆盖冻结代码、不重跑v1。在确认原授权尚未消耗真实生成次数后，新建此隔离修订，只修复来源记录器。对torch.classes/_classes.py与torch.ops/_ops.py分别留存虚拟模块记录；未知、缺失或哈希变更的真实项目文件仍被拒绝。4项定向测试通过。

两版本各预约一次、各加载模型一次，合计预约2次、实际generate仅1次；不能将预约数、模型初始化数和实际生成数混为一谈。v2登记要求v1零生成，并冻结v1全部源文件、原请求/claim、失败日志与失败审计。调用和审计再次检查该前置条件。本轮实际生成总预算已用尽，无第三次预约或第二次真实生成。

## 输入来源与独立验证

本次1240项冻结来源/输入包括模型权重与processor/tokenizer配置、实际项目依赖、旧证据与新脚本；旧四份生成相关依赖也纳入冻结。生成前保存实际input_ids、attention_mask、mm_token_type_ids、image_grid_thw、pixel_values的完整数组和SHA256，以及模板、解码后完整公共正文、实际生成配置和依赖版本。真实项目来源与两个虚拟命名空间分别记录，未把虚拟路径当文件放宽真实来源校验。

独立CPU作业6817不加载模型权重、不调用generate，从冻结RGB与请求重新应用processor模板，**全部5类张量逐元素一致**；独立重解析响应、核验EOS及白名单、比较全部历史动作、核查一次性claim和零规划/物理状态。见[独立审计](evidence/remote/run/audit_result.json)、[输入编码](evidence/remote/run/encoding.json)与[生成配置](evidence/remote/run/generation_config.json)。这些是输入/输出与来源证据，不证明模型内部为何选取该动作。

v1的6项协议测试与v2的4项定向测试合计10项不同测试通过，均在Slurm上运行。旧6808测试夹具错误、6809预期缺失实现失败、6811生成前工程失败、6812审计错误，以及v2的6813预期缺失实现失败均保留。6810/6814/6815/6816/6817及收尾作业的具体状态、退出码和用时见[作业记录](evidence/JOB_STATUS.txt)。无相关失败被改写为通过。

本地下载逐份SHA256校验，旧物理claim仍consumed=1，旧6732数值审计失败不变。见[同步清单](evidence/DELIVERY.json)、[服务器收尾](evidence/remote/run/delivery_inventory.json)与[本地最终验证](evidence/FINAL_VERIFICATION.json)。本地复核只读归档，不重跑服务器测试或实验。报告和本地归档复核器不属于已冻结的GPU执行源码。

## 下一步

本次“最多一次真实模型生成及独立审计”已收尾，物理和训练仍0。建议下一阶段只针对**这一个已保存新动作**登记零运动完整预检：抓取/放置端点、接近/持物运输/回程、闭合构型与原生命令入口，并独立复算；模型调用预算0。若任一步拒绝，记录标准阶段并停止；全部通过也仅得到静态可行候选，需独立执行登记后才考虑物理小试。本轮尚未启动该预检，不增加模型抽样或训练。

流程：brainstorming/writing-plans轻量计划、test-driven-development、systematic-debugging、verification-before-completion。无Git远程操作，无其他进程被中断。
