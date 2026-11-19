# 12条件机制资格结果

完成12/12；技术合格12；物理执行55/80；额外观测18。

| 条件 | 技术合格 | 机制暴露 | 观测到成功路径 | 各轨迹成功 |
|---|---|---|---|---|
| M0_940001_place_bias_occlusion | True | False | True | {'no_extra': True, 'reobserve': True} |
| M0_940002_place_bias_occlusion | True | False | True | {'no_extra': True, 'reobserve': True} |
| M1_940001_place_bias_occlusion | True | True | True | {'no_extra': True, 'reobserve': True} |
| M1_940002_place_bias_occlusion | True | False | True | {'no_extra': True, 'reobserve': True} |
| M0_940001_grasp_bias_outlier | True | True | True | {'latest': True, 'median': True} |
| M0_940002_grasp_bias_outlier | True | False | True | {'latest': True, 'median': True} |
| M1_940001_grasp_bias_outlier | True | False | True | {'latest': True, 'median': True} |
| M1_940002_grasp_bias_outlier | True | True | True | {'latest': True, 'median': True} |
| M0_940001_grasp_collision_side_effect | True | False | True | {'rule': True} |
| M0_940002_grasp_collision_side_effect | True | False | True | {'rule': True} |
| M1_940001_grasp_collision_side_effect | True | True | True | {'rule': True, 'alternate': True} |
| M1_940002_grasp_collision_side_effect | True | False | True | {'rule': True, 'alternate': True} |

A/B最多3次物理执行，C最多4次且有额外资格分支；不得跨机制合并成模型成功率。
B两组首次失败均获得同一状态的三次测量，仅聚合方式不同；不跨执行状态复用历史。
重观测是不可变物理快照的合成测量重采样；不是实时相机采集。原始测量和离群标签仅供审计。
model=null，模型调用0、训练批准0、最终测试未用；技术审计通过不等于机制暴露或方法有效。
无额外观测与重观测的资源差异是显式干预；不得归因于大模型。有限分支未成功不等于无解。
