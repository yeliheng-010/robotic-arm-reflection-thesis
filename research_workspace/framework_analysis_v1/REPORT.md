# 框架历史消融：只读归因

重新审计 480 任务；3117 个来源文件hash未变。
新物理执行0，新模型调用0，新训练输入0，最终测试未读取。

| 预算 | 配对决策 | 非空历史位置 | 相同当前输入 | 相同输入同选 | 相同输入异选 |
|---|---:|---:|---:|---:|---:|
| 3 | 84 | 27 | 84 | 84 | 0 |
| 4 | 89 | 32 | 89 | 89 | 0 |

## 预算4的历史组：信息与决策结构

- decisions: 89
- history_nonempty: 32
- single_candidate: 0
- selected_measured: 31
- agrees_with_rule: 77
- current_state_nondefault: 32
- ideal_error_stage: 89
- measured_or_stage_specific_option: 85
- selected_past_failed_state: 0
- next_attempt_success: 55
- measured_option: 75
- missing_residual: 14
- historical_measurement_available: 4
- past_failed_option_available: 3
- candidate_counts: {9: 44, 8: 16, 7: 10, 5: 16, 4: 2, 6: 1}
- choices: {'exploratory_lift': 36, 'descent_route': 18, 'measured_grasp': 15, 'measured_place': 16, 'exploratory_depth': 2, 'exploratory_place': 2}

## 对解释的约束

首个失败后的决策历史必为空；只有后续决策可检验历史贡献。两个预算共享前缀，不相加当独立证据。
measured_option表示规则已利用可见残差计算具体候选，不保证物理成功；stage_specific为候选结构描述，不是正确答案标签。
规则一致性是在模型实际遇到的状态上重算，不代表完整规则轨迹与模型轨迹相同。
当前参数/姿态可携带既往修正信息；删除显式历史不等于移除全部过去行为的影响。
有历史读入但输出相同，不能证明模型没读历史，也不能证明所有任务都不需要历史。
exact observable matches只搜索预算4历史组的89或实际决策数；未找到不同历史同输入不代表理论上不存在。

## 失败及规则独胜条件

- b3 H0_920018_grasp_place: rule_only=True; terminal=object_outside_container/unknown; residuals=['placement_residual_xy']
- b3 H1_920017_grasp_collision: rule_only=False; terminal=object_outside_container/unknown; residuals=['placement_residual_xy']
- b3 H1_920019_grasp_collision: rule_only=False; terminal=collision/place_descent; residuals=['grasp_residual_xy']
- b3 H1_920020_grasp_collision: rule_only=True; terminal=object_outside_container/unknown; residuals=['placement_residual_xy']
- b3 H1_920019_grasp_place: rule_only=False; terminal=object_outside_container/unknown; residuals=[]
- b4 H1_920020_grasp_collision: rule_only=True; terminal=collision/place_descent; residuals=[]
- b4 H1_920019_grasp_place: rule_only=False; terminal=object_outside_container/unknown; residuals=[]

详细决策特征见decisions.json，逐条件轨迹与分歧见cases.json；下一阶段设计另见NEXT_PLAN.md。
