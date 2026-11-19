# v2单次求解与独立审计：获得几何合格的新初态候选

**6875两侧SLSQP均成功，6876独立MuJoCo运动学与状态掩码审计通过，已保存新的candidate_state.npz。** 本轮解决了该候选的手指几何准入问题；完整场景禁碰、attach、视觉资格和动力学稳定性仍未验证，原生产动作rejected/gripper_closure保持。

本轮执行依据[冻结方案](PLAN.md)及[RULES副本](RULES.json)，新授权仅限几何构造。旧v2规则文件中execution_authorized=false保留为历史截点；实际本轮授权另存本目录，geometry_execution_authorized=true、dynamics_execution_authorized=false。没有复用旧claim或修改v1拒绝结果。

## 单次求解结果

每侧均从原after状态的参考角裁剪初值开始，调用一次冻结v2适配器；未使用6869失败尝试热启动，无重启、多起点或补搜。ftol=1e-14、maxiter=200及全部原物理门槛保持。

|侧别|优化器结果|报告迭代数|函数评价数|保存的主要迭代回调点|真实优化器调用|
|---|---|---|---|---|---|
|right|status=0，success=true|48|215|44|1|
|left|status=0，success=true|14|26|10|1|

回调点数量不是优化器报告的迭代数，不包含内部线搜索或Hessian。完整终止信息、初值、上下界、逐点目标与约束见[右侧结果](evidence/remote/run/right_result.json)、[左侧结果](evidence/remote/run/left_result.json)。两侧success通过后才组装和保存候选。

|侧别|coupler角(rad)|spring_link角(rad)|follower角(rad)|最大相对原角变化(rad)|
|---|---|---|---|---|
|right|-2.303929616531697e-18|0.0025894645641642965|-0.002476146769574794|0.0020441423849017117|
|left|-9.215718466126788e-19|0.00258946450772425|-0.0024761467155962474|0.002045889390896882|

最大改动低于原0.01rad上限，8个手指关节均处于原范围。构造进程只进行XML代数求解，模型/数据/Spec构造及积分请求均0。新候选来源仍是原6859的after积分状态，属于人工合成几何起点，不能称为未经修改的自然快照。

这一次成功验证了本候选的局部求解结果。v2同时改变变量参数化、显式Jacobian及几何回调实现，不能据此确定v1失败的唯一原因，也没有证明全局最近解、唯一解或其他输入下普遍收敛。

## 独立审计与状态保持

6876在独立进程用原XML编译1个无接触/驱动的隔离MuJoCo模型；仅使用mj_kinematics。编译后的关节限位、连接及driver等式参数与原记录一致，积分状态time/qpos布局也单独检查。

- 两侧完整三维连接残差的最大绝对世界分量均为1.1102230246251565e-16m，低于原1e-7m门槛；与构造XML公式的世界/根体局部向量在1e-12m审计一致性阈值内吻合。
- driver等式残差5.6718579052178475e-11rad，低于原1e-7rad门槛；两个driver角原样保持。
- 仅积分状态索引15、16、17、19、20、21改变，对应两侧6个被动角；其余字段与来源逐元素精确相等。包括机械臂、自由基座、场景物体、控制、时间及其他积分状态。
- NPZ中的reference与原after状态逐元素相等；候选的6个角与两侧求解结果精确一致。审计独立重做限位、改动上限与driver检查。

审计允许计数为隔离模型1、数据对象2；普通forward、渲染、优化器及积分均0。`motion_counts.model_construction=0`表示未触发禁止构造入口，允许的1个模型另记在allowed_counts，不能把整个审计称为“没有模型构造”。

候选文件：[candidate_state.npz](evidence/remote/run/candidate_state.npz)。SHA256：`f36b22f5fef62ce9d66feb0c9de61a0905a890e5c669a4744bdc60a55c808596`。独立审计见[audit_result.json](evidence/remote/run/audit_result.json)，candidate_verified=true，但production_ready=false。

## 作业、测试与归档

|作业|内容|状态/退出码|用时|
|---|---|---|---|
|6874|9项新增入口测试、来源核验及几何授权登记|COMPLETED / 0:0|52秒|
|6875|左右各一次真实SLSQP、候选保存|COMPLETED / 0:0|53秒|
|6876|独立隔离MuJoCo审计|COMPLETED / 0:0|52秒|

新增测试覆盖独占claim、先有构造claim再消费侧别claim、授权及预算拒绝、布尔预算拒绝、允许的被动角修改、driver/其余状态不许改动、改动上限、原限位、driver等式与任一侧失败整候选拒绝。没有重复运行旧12项测试或旧求解；这些是定向入口测试，不声称本轮经历红绿TDD。

每个进程核验8448项旧指纹及新绑定来源，原v4 claim=1/失败、6869拒绝、6873验证结果保持。构造、right、left、audit四份一次性记录均保留，构造预算已消费，不能重复提交construct.sbatch。队列为空，无初始化、闭合、模型生成或训练。

48份远端证据已逐份SHA256同步，包括授权、逐侧claim及结果、候选NPZ、独立审计、日志、6份新入口Python源和6份冻结v2 Python源。见[下载清单](evidence/DELIVERY.json)、[最终核验](evidence/FINAL_VERIFICATION.json)与[本地档案复核器](verify_archive.py)。本地仅复核哈希、源码、保存数组与结果字段，不执行新几何求解或仿真。

串行自审覆盖授权范围、独占记录、每侧一次调用、原参数绑定、状态修改范围和不同几何实现的对照。采用定向验证与verification-before-completion；没有Git操作。

## 当前阶段与下一步

当前已取得通过独立几何审计的新初态候选，可以进入**完整场景的零积分准入检查**。下一步建议固定这一个候选，核验完整模型/状态布局、attach约束、全场景禁碰及相关资格条件；先确认能在不隐藏执行初始化积分的前提下恢复场景。本轮未实施该检查。

隔离模型没有碰撞几何，不能证明夹爪不碰托盘；历史闭合包络碰撞风险仍未解除。完整场景检查通过之后，才有依据考虑单独登记有限闭合动力学预算。
