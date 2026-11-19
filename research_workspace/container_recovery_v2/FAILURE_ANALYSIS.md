# 初始失败分析

11个失败全部纳入恢复；4空抓和5碰撞发生在抓取阶段，2个IK失败发生于运输阶段。
IK失败不能依据仍存在的抓取残差判为抓取偏移；本轮先检验原候选空间，不按结果追改规则。
静态几何预检不保证动态路径无碰撞，现有证据不能直接判定不可恢复。

| 条件 | 错误 | 阶段 | 接触对象 | 修正候选数 |
|---|---|---|---|---:|
| L0_950401_randomized | empty_grasp | grasp_pose | [] | 7 |
| L0_950411_randomized | ik_failure | carry_transport | [] | 7 |
| L0_950416_randomized | empty_grasp | grasp_pose | [] | 7 |
| L1_950418_randomized | collision | grasp_pose | [['2f85_base', 'BlueBin']] | 7 |
| L0_950420_randomized | collision | grasp_pose | [['2f85_base', 'RedBin']] | 7 |
| L0_950421_randomized | ik_failure | carry_transport | [] | 7 |
| L0_950424_randomized | empty_grasp | grasp_pose | [] | 7 |
| L0_950426_randomized | collision | grasp_pose | [['2f85_base', 'RedBin']] | 7 |
| L1_950429_randomized | empty_grasp | grasp_pose | [] | 7 |
| L1_950436_randomized | collision | grasp_pose | [['2f85_base', 'BlueBin']] | 7 |
| L1_950440_randomized | collision | grasp_pose | [['2f85_base', 'BlueBin']] | 7 |

