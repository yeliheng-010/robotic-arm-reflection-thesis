# 观测决策诊断

物理快照完成11/11；唯一执行66。

| 选择器与固定补看数 | 下一次成功 | 实际物理执行 | 逻辑补看费用 |
|---|---|---|---|
| rule_l0 | 0/11 | 11 | 0 |
| rule_l1 | 5/11 | 11 | 11 |
| rule_l2 | 6/11 | 11 | 22 |
| model_l0 | 1/11 | 11 | 0 |
| model_l1 | 6/11 | 11 | 11 |
| model_l2 | 7/11 | 11 | 22 |

提示诊断（各分母及无效输出保留）：
{'baseline__base_current': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'unified_first__base_current': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'unified_last__base_current': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'missing_directive__base_current': {'total': 41, 'valid': 41, 'observe': 41, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 11}, 'comprehension__base_current': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 39, 'missing': 11, 'observe_when_missing': 0}, 'baseline__base_history': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'unified_first__base_history': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'unified_last__base_history': {'total': 41, 'valid': 41, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'missing_directive__base_history': {'total': 41, 'valid': 41, 'observe': 41, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 11}, 'execute_0__base_current': {'total': 11, 'valid': 11, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'execute_1__base_current': {'total': 11, 'valid': 11, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}, 'execute_2__base_current': {'total': 11, 'valid': 11, 'observe': 0, 'probe_correct': 0, 'missing': 11, 'observe_when_missing': 0}}

固定原失败快照选择新配置，再按相同场景种子重置执行一次，不是恢复仿真失败瞬间。
补看数固定为0/1/2，两选择器共享同快照噪声前缀；模型的执行选择阶段禁止继续补看但保留真实预算。
明确缺测指令属于专家策略注入，不能当作模型自主理解或学习收益。费用探针检验显式定义的读取，不代表物理决策能力。
来源为旧开发集的全部缺测快照，条件/种子相关，结果不是新独立样本、完整闭环成功率或最终测试。
首次/末尾菜单变体用于检查位置敏感性；所有提示均在结果前冻结，不挑赢家。无训练，无自动标签生成。
