# v1诊断工程故障留档

冒烟4882两个分片因静态副本缺少基座/工具/IK分支而异常退出（1:0），无合格完整执行摘要。根因为Robot.__getstate__/__setstate__没有复制这些状态。冻结代码与日志保留，未原地修改后重跑。

修复在descent_pose_v2，真实机器人副本回归测试先失败后通过；有效实验分母另行登记。后续descent_route_v1完成了下降旋转路径验证。请从descent_route_v1/REPORT.md和NEXT.md继续，不续跑本目录。
