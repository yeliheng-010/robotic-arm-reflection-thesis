# 三容器随机布局资格实验

这是无故障单次执行资格评估，不是模型/反思改进实验，也不是训练数据验收。

| 布局 | 计划条件 | 实际执行 | 成功 | 几何拒绝 |
|---|---:|---:|---:|---:|
| original | 80 | 80 | 80 | 0 |
| randomized | 80 | 80 | 69 | 0 |

40个布局种子，每种布局复用两个任务；原布局重复不能当作80种不同几何场景。
所有失败保留。需结合失败类型决定下一轮可达性/控制器修复，不自动按成功筛选训练数据。
没有新增微调，没有使用最终盲测。

## 首个预登记种子的前后画面

### L0_950401_original

![原始仿真初态](runs/L0_950401_original/attempt_1/attempt_1/before.png)

### L0_950401_randomized

![原始仿真初态](runs/L0_950401_randomized/attempt_1/attempt_1/before.png)

### L1_950401_original

![原始仿真初态](runs/L1_950401_original/attempt_1/attempt_1/before.png)

### L1_950401_randomized

![原始仿真初态](runs/L1_950401_randomized/attempt_1/attempt_1/before.png)

