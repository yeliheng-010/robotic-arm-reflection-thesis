# 独立种子观测聚合验证

完成24/24条件；资格通过24；物理执行93/144。
独立种子组12；方法latest/median；模型调用0。

| 预算 | latest成功/执行 | median成功/执行 | latest/median物理尝试 | latest/median额外观测 | latest独胜/median独胜 |
|---|---:|---:|---:|---:|---:|
| 1 | 5/24 | 5/24 | 24/24 | 0/0 | 0/0 |
| 2 | 19/24 | 22/24 | 43/43 | 38/38 | 0/3 |
| 3 | 22/24 | 24/24 | 48/45 | 38/38 | 0/2 |

## 全条件记录

| 条件 | 资格 | 相关离群出现 | latest/median成功 | latest/median轨迹长度 |
|---|---|---|---|---|
| V0_940101_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940101_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V0_940102_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940102_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 3, 'median': 2} |
| V0_940103_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940103_grasp_bias_outlier | challenge | True | {'latest': False, 'median': True} | {'latest': 3, 'median': 2} |
| V0_940104_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940104_grasp_bias_outlier | easy_control | False | {'latest': True, 'median': True} | {'latest': 1, 'median': 1} |
| V0_940105_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940105_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V0_940106_grasp_bias_outlier | easy_control | False | {'latest': True, 'median': True} | {'latest': 1, 'median': 1} |
| V1_940106_grasp_bias_outlier | easy_control | False | {'latest': True, 'median': True} | {'latest': 1, 'median': 1} |
| V0_940107_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940107_grasp_bias_outlier | challenge | True | {'latest': False, 'median': True} | {'latest': 3, 'median': 2} |
| V0_940108_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 3, 'median': 3} |
| V1_940108_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V0_940109_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940109_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V0_940110_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940110_grasp_bias_outlier | challenge | True | {'latest': True, 'median': True} | {'latest': 3, 'median': 3} |
| V0_940111_grasp_bias_outlier | easy_control | False | {'latest': True, 'median': True} | {'latest': 1, 'median': 1} |
| V1_940111_grasp_bias_outlier | easy_control | False | {'latest': True, 'median': True} | {'latest': 1, 'median': 1} |
| V0_940112_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |
| V1_940112_grasp_bias_outlier | challenge | False | {'latest': True, 'median': True} | {'latest': 2, 'median': 2} |

预算曲线事前冻结，从最多3次的同一执行轨迹截断，不能相加当三组独立实验。
两方法首次失败均使用同一状态的相同三次合成测量，观测费用一致；状态变化后不复用旧测量。
预算1没有修正决策，因此额外观测计费为0；表中尝试按方法轨迹计费，共享首次执行不在独立物理执行总数中重复计算。
资格跳过与实际执行分开；easy_control、无相关离群、无收益和失败条件均保留。
这是新训练资格种子上的开发验证，非最终盲测；同种子两物体相关，不宣称统计显著。
同状态短窗口中位数为规则聚合，不是模型微调或跨执行长期记忆；原始残差仅用于审计。
BUDGET_CURVES.json提供逐种子/逐条件配对结果；FAILURES.json保留最终失败轨迹。
训练批准0、最终测试未读取，旧pilot结果不并入本轮分母。
