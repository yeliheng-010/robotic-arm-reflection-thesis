# 逐场景证据索引

case 使用服务器目录中的零基编号；归因置信度见表格。

## Flash 的 14 个失败条件

|case|物体/注入/因素|实际错误链|主分类|依据与边界|
|---|---|---|---|---|
|07|RedBlock/calibration/layout|object_dropped → object_dropped → object_dropped|策略选择或参数语义|Flash 将抓取偏移舍入为 [-0.04,0,0]，残差降至约 3 mm 但仍脱落；后改抬升高度仍失败。规则按观测残差做双轴修正后成功。 结果差异已确认，精度机制待单变量验证|
|11|RedBlock/calibration/mixed|object_dropped → object_dropped → object_dropped|策略选择或参数语义|首轮残差缺失，Flash 同时改 Z 偏移和时间倍率；第二轮已有约 4 cm XY 残差却未修正，并将 1.5 降到 1.0 解释为减小惯性。规则第二轮利用可见残差后成功。 输入缺失与时间倍率误解已确认|
|25|PurpleCapsule/none/layout|empty_grasp → object_dropped → object_dropped|夹持或执行问题待辨析|空抓后换候选 1，随后抬升脱落；降低抬升距离仍脱落。规则换候选后减速也失败。相同首轮请求在 case37 产生另一种修正并成功。 失败链已确认，不能证明场景不可解|
|29|PurpleCapsule/none/mixed|object_dropped → object_dropped|无效修正|首次将 lift_height 调到 0.45，第二次原样再次给 0.45，被无变化校验拒绝；提示中已有当前参数和一条历史。 解析器与原始输出确认|
|31|PurpleCapsule/calibration/layout|ik_failure → ik_failure → ik_failure|策略选择或参数语义|IK 失败后连续换候选 1、2，约 4 cm Y 偏差始终未消除；规则修正 XY 偏移后成功。 同条件策略差异已确认|
|32|PurpleCapsule/calibration/sensor|collision → collision → collision|残差方向理解错误|残差定义为指令位置减物体位置，Flash 却沿负残差继续负向修正；抓取残差模长约 4.7→9.7→14.7 cm，碰撞持续。 语义、数值和轨迹共同确认|
|33|PurpleCapsule/calibration/physics|collision → collision → collision|残差方向理解错误|同样将负残差解释为物体在负方向，两次扩大负偏移，残差约 4.7→9.4→14.0 cm，持续碰撞。 语义、数值和轨迹共同确认|
|34|PurpleCapsule/calibration/feedback|collision → collision → collision|残差方向理解错误|在模拟反馈误差下仍将负残差直接当负向修正，真实残差持续增大，碰撞未解除。 加噪后的可见证据仍足以确认方向错误|
|35|PurpleCapsule/calibration/mixed|ik_failure → ik_failure → ik_failure|策略选择或参数语义|IK 失败后连续换候选 1、2；反馈仍显示较大 Y 偏差。规则本条件也失败，不能直接套用 case31 的成功结论。 失败链已确认，具体可行修正待验证|
|41|PurpleCapsule/collision/mixed|object_dropped → object_dropped|无效修正|先调 lift_height=0.45，后再次给同值，被校验拒绝；该碰撞标签条件实际先发生脱落。 与 case29 的请求和重复输出一致|
|42|PurpleCapsule/placement/clean|object_outside_container|无效修正|放置残差 X 约 0.31 m，模型输出 place_offset=-0.31 m，超过 ±0.25 m 边界；规则同样越界。 参数边界与原始输出确认|
|43|PurpleCapsule/placement/layout|empty_grasp → object_dropped → object_dropped|夹持或执行问题待辨析|先空抓，再两次抬升脱落，放置偏差还未成为本次失败的直接原因。 实际未到达注入的放置阶段|
|46|PurpleCapsule/placement/feedback|object_outside_container → object_outside_container → object_outside_container|策略选择或参数语义|模型把 candidate_index 称为“候选放置位置”，连续换 1、2，未改变 place_offset，物体仍在容器外。该字段实际选择抓取候选。 参数用途误解在原文中明确出现|
|47|PurpleCapsule/placement/mixed|object_dropped → object_dropped → object_dropped|夹持或执行问题待辨析|把 time_scale 从 1 降到 0.6 解释为减速，实际加快运动；随后改到 1.5 仍在抬升时脱落。 倍率语义错误已确认，持续脱落根因未证明|

## Flash 与规则结果不同的 8 个条件

|case|Flash|规则|证据解释|
|---|---|---|---|
|07|失败|成功|规则按完整双轴残差修正成功；Flash 舍入偏移后仍脱落并改抬升。精度机制待控制变量验证。|
|11|失败|成功|首轮反馈缺失，第二轮已恢复；规则利用第二轮残差成功，Flash 未修正 XY 且误解时间倍率。|
|22|成功|失败|规则将缺失的放置残差默认为零，生成不变参数而提前结束；Flash 试探后拿到第二轮残差并修正成功。|
|23|成功|失败|同样包含规则在缺失残差时提前退出的问题；模型成功不能全部归因于更强故障推理。|
|30|成功|失败|规则在抓取阶段碰撞时调整只在后续搬运生效的 lift_height；Flash 调整抓取 XY 后成功。|
|31|失败|成功|规则修正较大 XY 偏差后成功；Flash 连换抓取候选仍 IK 失败。|
|37|成功|失败|Flash 下调抓取 Z 约 1 cm 后成功；规则换候选后仍失败。与 case25/43 首轮请求完全相同但模型动作不同，需重复实验。|
|44|成功|失败|规则的放置修正超出边界而中止；Flash 先给合法 -0.25 m，随后根据过冲反馈改成 -0.20 m 并成功。|

## 重复请求

按完整请求负载（含 messages、温度、seed、模型、预算）比较，未删除任何条件。
- case25/attempt1, case37/attempt1, case43/attempt1：2 种回答文本，2 种解析动作。
- case25/attempt2, case43/attempt2：2 种回答文本，1 种解析动作。
- case29/attempt1, case41/attempt1, case47/attempt1：2 种回答文本，2 种解析动作。
- case29/attempt2, case41/attempt2：1 种回答文本，1 种解析动作。
