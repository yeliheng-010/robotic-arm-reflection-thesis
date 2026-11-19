---
date: 2026-11-18
status: serialization_fixed_frozen_snapshot_constraints_diagnosed
new_integration_steps: 0
isolated_kinematic_models: 1
full_scene_created: false
dynamics_validated: false
---

# 初态记录已修复：连接残差来自原冻结快照

承接[6859初态保存失败](../qualified_closure_dynamics_run_v4/REPORT.md)。本轮在独立新模块中修复NumPy布尔序列化，3项prepare实际写入回归先红后绿。零积分运动学诊断及独立刚体公式审计确认：**两处连接残差在放置机械臂之前就已存在于原冻结快照；前后8个手指角完全一致，局部残差保持。** 原快照还存在两处coupler限位超出，不能只修JSON就继续闭合。

## 修复交付

新[initial.py](initial.py)与冻结旧版仅一处差异：将finger_limits比较结果显式转换为Python bool。没有改变关节范围、CONNECT/DRIVER/ATTACH容差、状态构造、保存顺序或拒绝规则。

6861以旧实现副本运行3项真实NumPy数组经prepare写JSON测试，全部复现bool_序列化异常；6862在单行修复后全部通过。测试覆盖合法初态接受、连接约束拒绝时仍能写完整JSON、限位越界仍拒绝。场景操作全部使用替身，未运行真实初始化。

旧initial.py、旧v4入口、6859的截断initial.json和已耗claim保持不变。修复交付为新模块，尚未建立调用它的新动力学入口；不得重跑旧v4执行器。诊断产生的[重建报告字段](evidence/remote/run/reconstructed_report_subset.json)明确reconstruction_only=true，不替换原失败文件。

## 零积分诊断与证据来源

服务器没有可复用的完整MJB。6864从冻结夹爪XML创建一个**隔离运动学模型**，保留刚体层级、关节几何和连接等式，移除视觉/接触几何及驱动，并给根体添加仅用于满足编译条件的占位惯性。核对8个关节范围及3项编译等式的名称/参数一致；该模型不能用于解释接触、力或动力学，也不是完整任务场景重建。

诊断核验MuJoCo积分状态API的time/qpos前缀，结合冻结全模型关节地址提取状态。变换前完整积分状态与原始source_state.npz逐元素一致；变换前后8个手指关节值逐元素一致。只调用mj_kinematics，积分、完整环境、渲染、普通mj_forward均被阻断且请求计数0；实际隔离模型构造1次、数据对象分配3次。

6865在独立进程中禁止全部MuJoCo构造和积分，从原XML读取四元数、轴角、关节锚点和父子刚体变换，以独立公式复算两处连接残差。与隔离模型和6859已保存运行残差均在1e-12m数值重现容差内一致。该容差仅用于比较两个实现，原1e-7m连接门槛没有改变。详见[诊断结果](evidence/remote/run/result.json)和[独立公式审计](evidence/remote/run/audit_result.json)。

## 结果及其含义

|连接约束|变换前世界分量最大值|变换后世界分量最大值|前后残差向量模长|
|---|---:|---:|---:|
|id=0|42.766975微米|45.426990微米|约45.485880微米|
|id=1|42.810854微米|34.509014微米|约45.532559微米|

两者变换前后均超过原0.1微米门槛。世界坐标分量随夹爪旋转而变化；夹爪局部向量保持，说明放置变换没有产生新的连杆相对形变。因为before与原快照完全相等，这些非零残差早已存在于冻结输入中，而非本次新初始化或放置步骤产生。

保存数值还显示：

|关节|变换前后角度|冻结允许范围|
|---|---:|---:|
|right_coupler_joint|0.0001464011158215543 rad|[-1.57, 0] rad|
|left_coupler_joint|0.0001464008206692715 rad|[-1.57, 0] rad|

两项均在上限0之外，前后完全相同。6864的原限位计算拒绝这两项，本地档案复核又从保存向量和冻结范围核对了数值。连接残差的独立审计以两套运动学实现交叉验证；限位判断是保存标量与原边界的直接比较。

由此可以确认当前问题是**原冻结快照不满足这套诊断要求的严格几何初态条件**。本轮没有追溯生成该快照的全部动力学历史，不能将软约束、求解器或某个参数断言为唯一成因。没有进行关节投影、修改快照、额外settle或放宽任何阈值。

## 验证、归档与后续

|作业|内容|结果|
|---|---|---|
|6861|3项原错误回归|FAILED/1:0，3处预期序列化错误，5秒|
|6862|单行修复后回归|3项通过，COMPLETED/0:0，4秒|
|6863|来源登记|8427指纹，构造/积分0，COMPLETED/0:0，62秒|
|6864|保存状态的隔离运动学诊断|COMPLETED/0:0，37秒；积分0、完整场景0|
|6865|独立XML刚体公式审计|COMPLETED/0:0，37秒；构造/积分0|

37份来源、快照、原始输入、日志和结果已逐份SHA256同步，见[下载清单](evidence/DELIVERY.json)。[本地档案核验器](verify_archive.py)核对旧8401项指纹保持、9份新冻结Python源、原快照一致性、保存角度与限位、审计结果及单行修复范围，结果见[最终核验](evidence/FINAL_VERIFICATION.json)。服务器队列为空。

本轮新增初始化/任务积分/闭合均0，没有模型生成、完整抓放或训练。新目录的diagnostic_claim与audit_claim仅对应零积分诊断，不是新动力学授权；旧v4 claim=1、原失败和原生产rejected/gripper_closure保持。

下一步建议先制定一个满足现有严格约束的**新合成初态方案**，明确是否及如何调整手指初始角、与旧快照的差异及适用范围，先做零积分可行性验证。旧快照与新构造态不能混称同一初态；本轮没有执行该调整、准备新动力学入口或登记新轨迹预算。

采用systematic-debugging、executing-plans、定向TDD和verification-before-completion；按requesting-code-review检查项[串行自审](REVIEW.md)。独立审计为单独Slurm进程，无子代理或Git操作。PLAN/REVIEW保留冻结时版本，最终状态以本报告和CURRENT_STATUS为准。
