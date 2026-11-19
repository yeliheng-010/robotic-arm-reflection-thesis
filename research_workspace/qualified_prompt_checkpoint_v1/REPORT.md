---
date: 2026-11-18
status: pre_generation_engineering_failure_audited
model_reservations: 1
actual_model_generations: 0
physical_attempts: 0
training_runs: 0
---

# B提示词验证v1：来源记录器在真实生成前中止

用户授权最多1次真实模型生成，规划/物理/训练均0。v1完成6项协议测试及1206项来源登记，在GPU作业6811中加载模型、编码输入后，来源记录器发生工程错误；**没有进入generate，没有模型回答，不能评价B提示词效果。** v1按[原协议](PLAN.md)停止，claim仍consumed=1，未修改或重新运行其冻结生成入口。

## 已确认的工程原因

记录器遍历sys.modules并读取每个模块的`__file__`。PyTorch的`torch.classes`和`torch.ops`是ModuleType派生的虚拟命名空间，类属性分别为`_classes.py`和`_ops.py`。v1把前者按运行工作目录解析为`/home/yeliheng/grasp_server/improvement_20261019/code/_classes.py`，继而因不在登记来源内拒绝。该路径并不存在；这不是模型输入被截断、模型重复动作或真实项目源码被篡改。

6812首次失败审计把该类属性误认为实例字典字段，断言失败；其源码和日志保留。6814的独立CPU审计改用已核实的类属性，确认两个虚拟名称、错误路径不存在，以及调用顺序为记录输入→生成开始标记→generate。`generation_started.json`、`response.json`、`result.json`和`generation_config.json`均不存在，实际生成0次；所有已保存输入张量独立重新编码逐元素一致。见[失败审计](evidence/remote/run/failure_audit.json)。

## 输入与授权范围

实际请求采用诊断阶段B草案的末尾decision_checkpoint，并将planning预算1→0；原系统、RGB、完整观测、历史、白名单、任务文本均保留。输入10725 token，未超过原16384限制。B之外的C文本清理没有启用。相对于历史基线有两处正文变化，因此不声称严格单变量因果验证。

图像、相机、全14/85%资格、尺寸/连通性/6mm标定、3mm深度噪声/2%缺失与全部安全门槛不变。没有proposal、预检、MuJoCo积分、物理或训练。

## 作业与失败保留

|作业|内容|结果|
|---|---|---|
|6808|首次TDD夹具|setUpClass报告ERROR，0项测试，保留|
|6809|修正夹具后的缺失实现检查|6项预期失败，保留|
|6810|协议测试与登记|6项通过；1206来源冻结|
|6811|唯一v1模型作业|输入记录阶段失败，generate调用0次|
|6812|首次CPU失败审计|属性位置假设错误，失败保留|
|6814|修正CPU失败审计|通过；零生成与输入张量独立核实|

详细状态/退出码/耗时随恢复版本的[最终作业记录](../qualified_prompt_checkpoint_v2/evidence/JOB_STATUS.txt)归档。上述测试未视为模型调用，模型初始化亦与generate次数分别记录。

## 隔离恢复与归档

当前用户授权是最多1次真实生成。零生成已独立证实后，在[隔离v2](../qualified_prompt_checkpoint_v2/REPORT.md)冻结本目录全部原始来源、失败日志、claim和审计，仅修复来源记录器并完成原授权余下的1次真实生成。v1的“工程异常停止”仍成立；没有删除claim、覆盖旧源或重新提交v1作业。跨两版本预约共计2次，实际生成总上限仍1，不能把两次初始化/预约描述为一次。

本地证据见[下载清单](evidence/DELIVERY.json)与[最终归档验证](evidence/FINAL_VERIFICATION.json)。本地归档工具与此报告在运行后生成，不属于v1冻结的模型执行源码。没有Git操作或其他进程中断。
