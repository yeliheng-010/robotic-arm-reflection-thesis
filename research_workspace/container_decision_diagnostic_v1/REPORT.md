# 容器随机布局：候选选择与动作覆盖诊断

覆盖全部11个既有失败案例。先冻结44次模型决策，再执行73个物理分支。
每个分支从原布局/种子重置；一次第三尝试，不恢复失败瞬间。模型为基础4B，adapter禁用。
这是事后开发诊断，不能视作新独立测试，也不能将穷举候选的上界当作可部署策略成功率。

- 原候选空间至少一个动作成功：5/11
- 降低抬升高度至少一个动作成功：0/2（专家扩展）

| 模型输入 | 所选动作实际成功/11 |
|---|---:|
| replay | 1/11 |
| reverse | 0/11 |
| summary | 1/11 |
| expert_hint | 2/11 |

expert_hint额外给出规则启发式指导，不能称为无指导模型能力。
reverse仅改变候选及合法ID顺序；summary仅追加已发生历史与失败阶段提醒。
invalid计为未成功，无规则代选；物理失败保留于完整分母。

| 案例 | 初始错误 | 原候选可恢复动作数 | 低抬升可恢复动作数 |
|---|---|---:|---:|
| L0_950401_randomized | empty_grasp | 1 | 0 |
| L0_950411_randomized | ik_failure | 0 | 0 |
| L0_950416_randomized | empty_grasp | 1 | 0 |
| L1_950418_randomized | collision | 0 | 0 |
| L0_950420_randomized | collision | 0 | 0 |
| L0_950421_randomized | ik_failure | 0 | 0 |
| L0_950424_randomized | empty_grasp | 1 | 0 |
| L0_950426_randomized | collision | 1 | 0 |
| L1_950429_randomized | empty_grasp | 2 | 0 |
| L1_950436_randomized | collision | 0 | 0 |
| L1_950440_randomized | collision | 0 | 0 |

后续应先根据失败阶段改进候选或选择器，再用新种子进行冻结对照；本轮不训练、不使用最终盲测。
