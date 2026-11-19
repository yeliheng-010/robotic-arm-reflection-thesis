# 当前研究进度：完整抓放成功，批量评估因工程异常提前停止

更新日期：2026-11-19（America/Los_Angeles）。以下结果来自已经完成的服务器作业，没有重新运行实验。

## 目前做到哪一步

完整抓取、抬升、搬运、释放与回程链已经实际成功执行。单次作业6891成功1/1；随后200条件批量作业6892实际执行4次，其中3次完整成功、1次工程异常，剩余196个条件按预设规则跳过。汇总作业6895已经结束。

|指标|结果|含义|
|---|---:|---|
|预登记条件|200|五档XY偏移，各40个方向|
|实际完整任务尝试|4|都位于1mm偏移档|
|任务成功|3|接近、夹持、搬运、释放、稳定放置及回程完成|
|工程异常|1|夹持确认后的搬运路径检查中止|
|未执行条件|196|停止机制跳过，不能计为物理失败|
|已执行尝试内成功比例|3/4，75%|样本极少，不能代表整批或跨布局能力|
|执行覆盖|4/200，2%|结果记录齐全不等于物理执行完成|

## 当前问题

条件002：胶囊XY偏移半径1mm、方向18°。夹持确认后，持物路径检查通过ot_volume.body_pose调用SpatialMath的SE3.Rt，抛出ValueError: expecting SO3 or rotation matrix。该次执行3250任务步后停止；条件000、001、003各完成8250步。工程异常触发STOP.json，其余条件没有自动重试。

错误堆栈能定位失败入口，但尚不能证明旋转矩阵失效的数值根因。不能把这次异常直接归因于抓姿、夹持滑移或碰撞，也不能通过跳过矩阵检查来宣称修复。当前发布只归档已有结果，不修改冻结执行器、不重新提交作业。

## 本批究竟评估什么

复用种子978505的固定场景和最新保存动作，目标PurpleCapsule → RedBin；改变胶囊初始世界坐标XY位置，半径1/2/3/5/10mm，各40个等角度方向。机器人、目标箱、场景其余部分与动作保持。此前成功的中心条件6891不在本批分母中，不与3/4合并。

这是固定动作的位置扰动评估，尚未完成五档扫描，更不是200个随机场景或模型在线决策评估。新增模型调用0、训练0、独立事后审计0。运行时路径、碰撞、掉落与释放保护保留；历史静态闭合拒绝与观察资格拒绝没有改写为通过。

## 代码、资料和证据

- [批量原始汇总](../research_workspace/qualified_grasp_batch_v1/evidence/remote/summary.json)
- [全部200项去向](../research_workspace/qualified_grasp_batch_v1/evidence/remote/all_results.json)
- [停止原因与完整堆栈](../research_workspace/qualified_grasp_batch_v1/evidence/remote/STOP.json)
- [Slurm作业记录](../research_workspace/qualified_grasp_batch_v1/evidence/remote/slurm_status_20261119.txt)
- [单次完整抓放报告](../research_workspace/qualified_full_task_trial_v1/REPORT.md)
- [批量执行代码](../research_workspace/qualified_grasp_batch_v1/worker.py)与[汇总代码](../research_workspace/qualified_grasp_batch_v1/summarize.py)
- [全部代码与资料入口](CODE_AND_DATA.md)
- [11月11日历史进展](CURRENT_PROGRESS_20261111.md)

下一步技术工作应先解释并修复旋转矩阵检查异常，再在新版本中明确剩余196个未执行条件的续跑规则。本轮没有启动该修复或续跑；旧失败、claim和所有已完成实验保持。
