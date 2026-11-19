# 观测聚合只读归因

重新审计24条件，来源1082文件hash不变。
实际消费字段误差方向：{'higher': 5, 'lower': 13, 'equal': 1}；配对结果不同条件3。

| 条件 | 初始阶段 | 实际消费字段 | 最后测量离群 | latest/median误差(mm) | 误差方向 | 预算2/3配对 |
|---|---|---|---|---|---|---|
| V0_940101_grasp_bias_outlier | grasp_pose | grasp_residual_xy | False | 3.842/8.745 | higher | both_success/both_success |
| V1_940101_grasp_bias_outlier | grasp_pose | grasp_residual_xy | False | 7.243/9.753 | higher | both_success/both_success |
| V0_940102_grasp_bias_outlier | grasp_approach | grasp_residual_xy | False | 7.425/6.827 | lower | both_success/both_success |
| V1_940102_grasp_bias_outlier | carry_transport | grasp_residual_xy | True | 76.096/1.159 | lower | median_only/both_success |
| V0_940103_grasp_bias_outlier | grasp_approach | grasp_residual_xy | False | 10.085/3.282 | lower | both_success/both_success |
| V1_940103_grasp_bias_outlier | grasp_pose | grasp_residual_xy | True | 80.414/2.744 | lower | median_only/median_only |
| V0_940104_grasp_bias_outlier | grasp_pose | grasp_residual_xy | False | 1.519/1.571 | higher | both_success/both_success |
| V1_940104_grasp_bias_outlier | 无修正决策 | — | — | — | — | 初始成功或未执行，详见cases.json |
| V0_940105_grasp_bias_outlier | grasp_approach | grasp_residual_xy | False | 9.240/5.983 | lower | both_success/both_success |
| V1_940105_grasp_bias_outlier | unknown | placement_residual_xy | False | 8.544/8.544 | equal | both_success/both_success |
| V0_940106_grasp_bias_outlier | 无修正决策 | — | — | — | — | 初始成功或未执行，详见cases.json |
| V1_940106_grasp_bias_outlier | 无修正决策 | — | — | — | — | 初始成功或未执行，详见cases.json |
| V0_940107_grasp_bias_outlier | grasp_approach | grasp_residual_xy | False | 4.419/8.299 | higher | both_success/both_success |
| V1_940107_grasp_bias_outlier | place_descent | grasp_residual_xy | True | 82.097/6.267 | lower | median_only/median_only |
| V0_940108_grasp_bias_outlier | carry_lift | grasp_residual_xy | True | 88.417/86.708 | lower | both_fail/both_success |
| V1_940108_grasp_bias_outlier | grasp_pose | grasp_residual_xy | False | 8.384/2.703 | lower | both_success/both_success |
| V0_940109_grasp_bias_outlier | carry_lift | grasp_residual_xy | False | 5.568/4.566 | lower | both_success/both_success |
| V1_940109_grasp_bias_outlier | carry_lift | grasp_residual_xy | False | 1.294/5.486 | higher | both_success/both_success |
| V0_940110_grasp_bias_outlier | grasp_pose | grasp_residual_xy | False | 9.908/5.882 | lower | both_success/both_success |
| V1_940110_grasp_bias_outlier | grasp_pose | grasp_residual_xy | True | 92.193/85.277 | lower | both_fail/both_success |
| V0_940111_grasp_bias_outlier | 无修正决策 | — | — | — | — | 初始成功或未执行，详见cases.json |
| V1_940111_grasp_bias_outlier | 无修正决策 | — | — | — | — | 初始成功或未执行，详见cases.json |
| V0_940112_grasp_bias_outlier | carry_lift | grasp_residual_xy | False | 7.045/4.242 | lower | both_success/both_success |
| V1_940112_grasp_bias_outlier | unknown | placement_residual_xy | False | 5.761/5.010 | lower | both_success/both_success |

原阶段启发式未标记但动作消费了测量的条件：
['V1_940102_grasp_bias_outlier', 'V1_940107_grasp_bias_outlier']

实际消费表示selected.kind及facts.measurement引用此字段，不证明该字段是物理故障的正确归因。
原exposure/协议不改；本报告是补充的事后诊断，包含误差变大、无收益和失败。
候选参数和ID可能随观测变化，不能说两方法候选菜单完全一致。
cases.json保留三次可见测量、审计真值、有效测量、候选类型、完整选定动作和后续执行链。
审计真值/离群标记只用于离线分析，不可进入未来模型输入。
无新增物理执行、模型调用、训练或最终测试。
