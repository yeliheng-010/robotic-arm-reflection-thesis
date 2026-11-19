# 四组框架消融与预算对照

阶段：final；完成 480/480；审计通过：True。

| 执行预算 | 方法 | 成功/执行 | 失败后恢复/首次失败 | 总执行次数 | 模型调用 | 非法/服务错误 |
|---|---|---:|---:|---:|---:|---:|
| 3 | retry | 3/60 | 0/57 | 174 | 0 | 0/0 |
| 3 | rule | 57/60 | 54/57 | 144 | 0 | 0/0 |
| 3 | current | 55/60 | 52/57 | 144 | 84 | 0/0 |
| 3 | history | 55/60 | 52/57 | 144 | 84 | 0/0 |
| 4 | retry | 3/60 | 0/57 | 231 | 0 | 0/0 |
| 4 | rule | 59/60 | 56/57 | 147 | 0 | 0/0 |
| 4 | current | 58/60 | 55/57 | 149 | 89 | 0/0 |
| 4 | history | 58/60 | 55/57 | 149 | 89 | 0/0 |

retry保持参数重复执行；rule使用无历史候选与规则；current仅当前反馈；history额外读取历史。
两模型组均为基础4B，adapter禁用；启动时adapter回放只是服务身份检查，不计为方法任务。
预算3是主实验，预算4是独立敏感性分析；不可合并成一个成功率。
60开发条件共享6个批次内种子组；非独立60种子，非最终盲测，未用于本轮训练。
阶段与接触信息仍为理想信息，XY残差保持原噪声/缺失；结论限定仿真有限候选决策。
各反馈组共用不读取历史的候选；当前状态与尝试编号仍可见。旧版成功率不可直接混合。
恢复时间中的模型调用耗时包含服务排队，仅作运行成本记录，不作严格延迟基准。

## 配对成功差异

- b3_retry_vs_rule: {'right_only': 54, 'both_success': 3, 'both_fail': 3}
- b3_retry_vs_current: {'right_only': 52, 'both_fail': 5, 'both_success': 3}
- b3_retry_vs_history: {'right_only': 52, 'both_fail': 5, 'both_success': 3}
- b3_rule_vs_current: {'both_success': 55, 'left_only': 2, 'both_fail': 3}
- b3_rule_vs_history: {'both_success': 55, 'left_only': 2, 'both_fail': 3}
- b3_current_vs_history: {'both_success': 55, 'both_fail': 5}
- b4_retry_vs_rule: {'right_only': 56, 'both_success': 3, 'both_fail': 1}
- b4_retry_vs_current: {'right_only': 55, 'both_success': 3, 'both_fail': 2}
- b4_retry_vs_history: {'right_only': 55, 'both_success': 3, 'both_fail': 2}
- b4_rule_vs_current: {'both_success': 58, 'both_fail': 1, 'left_only': 1}
- b4_rule_vs_history: {'both_success': 58, 'both_fail': 1, 'left_only': 1}
- b4_current_vs_history: {'both_success': 58, 'both_fail': 2}

## 审计
- 同状态配对：{'paired_initials': 480, 'shared_state_outcome_checks': 1118, 'old_anchor_outcome_checks': 0, 'matched_inputs': {'feedback': 2043, 'candidates': 1245}}
- 预算前缀：{'tasks': 240, 'attempts': 606, 'decisions': 366}
- 逐条件、类型、噪声和种子指标见 verification JSON；不因成功率低而停止或删除样本。
