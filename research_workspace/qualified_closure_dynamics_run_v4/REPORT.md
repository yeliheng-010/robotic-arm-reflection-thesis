---
date: 2026-11-18
status: initial_state_save_failed_archived
diagnostic_claim_consumed: 1
setup_steps: 500
task_steps: 0
audit_integration_steps: 0
dynamics_validated: false
---

# v4完成初始化，但初态保存失败，闭合未启动

本次用户确认一次最多500初始化步＋1000闭合步及一次零积分审计。6858登记8401项冻结来源；6859通过GPU导入检查、消费独立claim并完成500步初始化，但保存合成初态时因NumPy布尔值无法JSON序列化而失败，闭合0步。6860零积分失败审计通过，**未重试，原失败及claim=1保留**。

## 新进展与实际失败位置

上一轮GPU导入阻塞本次没有复现，实际进入了场景创建、冻结状态恢复及合成初态构造。失败发生在qualified_closure_dynamics_v1.initial.prepare调用save写initial.json时：

```text
TypeError: Object of type bool_ is not JSON serializable
```

finger_limits由Python浮点界限与NumPy qpos标量比较产生，元素是numpy.bool_，未转换成Python bool。json.dump使用allow_nan=False但不支持该NumPy类型，写到该数组首个值时异常。[原initial.json](evidence/remote/engine/run/initial.json)因此是不完整JSON，按原字节保留，没有补写或修成假成功记录。

[失败记录](evidence/remote/engine/run/failure.json)保存setup_step_requests=500、task_step_requests=0。[执行日志](evidence/remote/execute-6859.log)及冻结代码顺序显示prepare之前的初始化已返回；尚未到保存MJB、创建Backend或run_loop。因此没有闭合轨迹或碰撞观察，不能把本轮称为“闭合失败”或“无碰撞”。

## 另一个已出现的问题：合成初态连接残差不合格

不完整initial.json的equalities字段已经完整写入，以下是其中的记录，审计只重新核对数值与原阈值的比较：

|约束|最大绝对残差|原容差|记录结果|
|---|---|---|---|
|connect，id=0|45.426990微米|0.1微米|不通过|
|connect，id=1|34.509014微米|0.1微米|不通过|

driver等式和attach检查记录为通过。冻结prepare在保存初态后要求全部限位及等式检查通过；已有两项false，因此**即使只修复序列化，该保存初态仍会被原规则拒绝，不能直接继续积分**。

本次没有保存MJB，审计没有构造新场景或独立forward重算残差。表格是完整字段中的原运行记录，不是新物理重建；尚不能判断残差来自冻结初态本身、放置变换，或柔性约束与严格静态容差的适用差异。不得为推进闭合而放宽门槛或额外settle。

## 单次零积分失败审计

[6860审计结果](evidence/remote/failure_audit.json)确认：

- 8401项来源保持；授权绑定、6859 claim=1和原失败一致，运行目录只有5份已有文件。
- NumPy标量比较生成bool_，纯数据序列化复现同一异常；这是最小类型复现，不是假称重新运行了真实初态。
- initial.json确实截断于finger_limits，已完整写入的4项等式记录，其数值阈值判断一致；两处connect不通过。
- initial_transform.npz的before/after积分状态向量形状一致且有限，原文件完整保留；没有借此声称所有几何约束已重建。
- 审计没有导入MuJoCo，没有场景创建或积分；不调用需要完整轨迹的正常审计器。

审计通过仅表示失败证据一致，不代表动力学验证通过。原测试覆盖了假后端停止/预算和GPU导入，未覆盖真实初态报告中的NumPy布尔序列化，不能将此前测试通过等同于这条真实路径通过。

## 作业与归档

|作业|内容|状态/退出码|耗时|
|---|---|---|---|
|6858|来源核验与独立预算登记|COMPLETED / 0:0|26秒|
|6859|唯一一次v4隔离诊断|FAILED / 1:0|80秒|
|6860|零积分失败证据审计|COMPLETED / 0:0|26秒|

25份来源、授权、日志、初态残留及旧claim已SHA256同步，见[下载清单](evidence/DELIVERY.json)。[本地档案核验器](verify_archive.py)核对来源、旧准备绑定、两份GPU检查、claim、完整与截断文件、作业状态及报告链接，结果见[最终核验](evidence/FINAL_VERIFICATION.json)。6份冻结v4 Python源和旧initial.py均保持，服务器队列为空。

本次轨迹claim消耗1、证据审计消耗1；未调用模型、完整抓放或训练，没有旧实验重跑、阈值变化或Git操作。旧v1 claim=1、旧v3授权与无run状态、6851失败保持。原rejected/gripper_closure仍有效。

下一步建议先用独立新版本修复初态报告的NumPy类型序列化，并对已有初态/变换证据进行零积分约束诊断，核清两处残差的来源和当前合成起点是否适用；不要只修JSON就申请新轨迹，也不降低原容差。本轮未实施该修复、未追加积分或重试。

采用executing-plans、systematic-debugging及verification-before-completion；按requesting-code-review检查项完成串行自审。6860是独立Slurm审计进程，不是子代理评审。冻结PLAN保留登记时文本，最终状态以本报告和CURRENT_STATUS为准。
