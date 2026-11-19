# 主动观测预算资格试验

完成24/24条件，48规则轨迹；物理执行122。

| 预算 | fixed_first成功 | adaptive成功 | 两者方法尝试 | 两者额外观测 |
|---|---|---|---|---|
| 1 | 1/24 | 1/24 | 24/24 | 0/0 |
| 2 | 10/24 | 10/24 | 47/47 | 46/39 |
| 3 | 15/24 | 16/24 | 61/61 | 46/42 |

机制暴露（决策次数，不是独立条件数）：
{'fixed_first': {'decisions': 37, 'missing': 15, 'conflict': 7, 'visibility_recovered': 5, 'later_observation': 0, 'unresolved': 29, 'phases': {'carry_lift': 8, 'unknown': 10, 'grasp_pose': 13, 'grasp_approach': 4, 'place_descent': 2}, 'multi_stage_conditions': 10}, 'adaptive': {'decisions': 37, 'missing': 15, 'conflict': 5, 'visibility_recovered': 6, 'later_observation': 3, 'unresolved': 27, 'phases': {'carry_lift': 8, 'unknown': 10, 'grasp_pose': 13, 'grasp_approach': 4, 'place_descent': 2}, 'multi_stage_conditions': 10}}

两策略均最多3次物理尝试、2次额外观测；实际观测费用可不同，全部报告。
fixed_first第一次失败取三次观测；adaptive以可见缺测、少于两次有效测量或>30mm冲突决定补看。
一致性不是校准概率，不代表多数离群已被排除。全部同状态样本取中位数；跨状态不复用。
缺测和离群共同形成压力条件，不宣称从本试验分离两噪声各自的因果作用。
数据用途为train_candidate资格试验，非最终测试；6种子组，不宣称统计显著。
单阶段/复合阶段分项与全部失败见BUDGET_CURVES.json、verification.json和原始tasks。
门禁仅检查工程正确性；是否实际缺测、冲突、再次观测和多阶段故障由结果另报。
本轮没有模型、历史推理或训练，不把规则分配效果称为模型收益。
