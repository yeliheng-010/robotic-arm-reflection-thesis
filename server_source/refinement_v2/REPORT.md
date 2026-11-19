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

smoke：failed，1/8。

|方法|成功/运行|条件数|无效输出|策略耗尽|
|---|---:|---:|---:|---:|
|rule_old|0/0|0|0|0|
|rule_new|1/1|1|0|0|
|flash_old|0/0|0|0|0|
|flash_new|0/0|0|0|0|

模型每条件重复三次，重复不是独立场景样本；需按条件聚合比较，不直接把 36 次当作 36 个独立条件。
这些条件来自已知失败复盘，只能作开发回归，不能据此宣称测试集泛化。

regression：尚无已落盘结果。

collision：running，6/12。

|条件|半高 m|默认成功|目标障碍碰撞|错误|
|---|---:|---|---|---|
|0|None|True|False|None|
|0|0.06|True|False|None|
|0|0.19|False|True|collision|
|0|0.25|False|False|grounding_off_target|
|0|0.3|False|False|grounding_off_target|
|0|0.35|False|False|grounding_off_target|

None 为禁用障碍物对照；0.06 m 为原始低障碍物。其他高度按预定网格扫描。
目标碰撞要求 collision 错误的接触对明确包含 SafetyDivider；单纯抓取失败不算有效碰撞注入。
保留所有未触发条件。该扫描不与原场景语义回归混合，且未用任何模型恢复结果挑选几何。
