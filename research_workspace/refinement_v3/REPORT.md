# 参数语义、专家规则与碰撞校准

范围：36 次离线诊断、8 次物理预检、96 次开发回归、12 次独立碰撞校准。
未启动 192 条件扩展或微调；封存测试未使用。

rule_new 的缺失测量探测来自显式专家规则；flash_new 仅追加通用参数语义，未修补模型回答。

diagnostic：completed，36/36。

|诊断|提示|合法回答|合法动作种数|
|---|---|---:|---:|
|bounds|flash_old|1/3|1|
|bounds|flash_new|3/3|1|
|candidate|flash_old|0/3|0|
|candidate|flash_new|0/3|0|
|direction|flash_old|3/3|2|
|direction|flash_new|3/3|2|
|duration|flash_old|3/3|1|
|duration|flash_new|3/3|2|
|missing|flash_old|3/3|2|
|missing|flash_new|3/3|2|
|repeat|flash_old|0/3|0|
|repeat|flash_new|3/3|1|

合法性不等于语义正确或物理成功；动作种数用于检查同输入的一致性。
direction_dot_products 为拟议抓取位移与展示残差的内积，负值仅支持方向一致，不能代替物理执行。

smoke：completed，8/8。

|方法|成功/运行|条件数|无效输出|策略耗尽|
|---|---:|---:|---:|---:|
|rule_old|0/2|2|1|0|
|rule_new|2/2|2|0|0|
|flash_old|2/2|2|0|0|
|flash_new|1/2|2|0|0|

模型每条件重复三次，重复不是独立场景样本；需按条件聚合比较，不直接把 36 次当作 36 个独立条件。
这些条件来自已知失败复盘，只能作开发回归，不能据此宣称测试集泛化。

regression：completed，96/96。

|方法|成功/运行|条件数|无效输出|策略耗尽|
|---|---:|---:|---:|---:|
|rule_old|3/12|12|4|0|
|rule_new|9/12|12|0|0|
|flash_old|10/36|12|3|0|
|flash_new|19/36|12|1|0|

模型每条件重复三次，重复不是独立场景样本；需按条件聚合比较，不直接把 36 次当作 36 个独立条件。
这些条件来自已知失败复盘，只能作开发回归，不能据此宣称测试集泛化。

collision：completed，12/12。

|条件|半高 m|默认成功|目标障碍碰撞|错误|
|---|---:|---|---|---|
|0|None|True|False|None|
|0|0.06|True|False|None|
|0|0.19|False|True|collision|
|0|0.25|False|False|grounding_off_target|
|0|0.3|False|False|grounding_off_target|
|0|0.35|False|False|grounding_off_target|
|24|None|True|False|None|
|24|0.06|True|False|None|
|24|0.19|True|False|None|
|24|0.25|True|False|None|
|24|0.3|True|False|None|
|24|0.35|True|False|None|

None 为禁用障碍物对照；0.06 m 为原始低障碍物。其他高度按预定网格扫描。
目标碰撞要求 collision 错误的接触对明确包含 SafetyDivider；单纯抓取失败不算有效碰撞注入。
保留所有未触发条件。该扫描不与原场景语义回归混合，且未用任何模型恢复结果挑选几何。

紫色胶囊路线校准（独立于模型回归）：

状态 completed，6/6，障碍 Y=0.84 m、X 范围 1.32—1.395 m。

|半高 m|默认成功|目标碰撞|错误|
|---|---|---|---|
|None|True|False|None|
|0.06|True|False|None|
|0.12|False|True|collision|
|0.15|False|True|collision|
|0.19|False|True|collision|
|0.22|False|True|collision|

原 Y=0.72 校准作业 4744 因几何与绿色圆柱重叠而停止，记录保留；Y=0.82 的宽障碍作业 4745 被初始 qpos 审计拦截，说明仅检查四个目标物体不足。本组使用完整场景中 57 个可接触几何体的边界检查，最小轴向间隔 0.0122 m，并在每次运行后核验初始 qpos。
没有调用模型，也没有按模型恢复结果选择障碍。
