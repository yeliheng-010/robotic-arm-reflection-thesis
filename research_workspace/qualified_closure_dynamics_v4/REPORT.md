---
date: 2026-11-18
status: gpu_import_preparation_audit_and_direct_entry_passed
execution_authorized: false
physics_steps: 0
model_calls: 0
training_runs: 0
dynamics_validated: false
---

# GPU导入来源修复完成，实际入口零积分检查通过

承接[6851的CPU/GPU导入差异失败](../qualified_closure_dynamics_run_v3/REPORT.md)。新v4已在与拟执行任务相同的GPU资源下完成真实导入登记、独立审计和实际执行入口检查。**7项新增测试通过，8401项指纹核验通过；三个GPU进程的构造和积分请求计数均为0。** 本轮没有新授权、run目录或claim，未运行闭合轨迹。

## 改动与解决的问题

旧v3在CPU作业准备，GPU执行时Open3D选择CUDA扩展，未登记来源导致入口拒绝。v4准备、独立审计、直接入口检查统一申请GPU1、CPU2、16G、10分钟，实际均为Tesla V100-SXM2-16GB。代码要求Slurm分配GPU，Torch和Open3D各可见1设备，Open3D实际后端为cuda；型号与计算能力也登记并核对。

沿用冻结v3的来源分类、发行包记录、原生子模块与进程别名核验，不只补一个二进制、不绕过未知模块检查。旧CPU集合及历史证据指纹保留；新GPU进程实际加载的模块、文件、安装记录另行完整登记。此前拒绝的open3d/cuda/pybind扩展已进入新快照与授权候选指纹，哈希与6852事后检查一致，并匹配当前安装RECORD。

执行入口新增--verify-imports模式，直接使用同一个checked_imports实现。在未授权状态下只检查来源与GPU配置，独立保存结果，不创建claim、不调用环境。普通执行路径仍先检查独立v4授权，再检查真实导入，最后才consume。未知参数拒绝，防止误拼检查参数落入执行路径。

真实环境运行函数与v3逐节点AST一致，固定输入、原500/1000步上限、控制序列和禁碰停止逻辑未变。本轮只运行检查模式，未生成可直接发起动力学的execute.sbatch或authorization.json。

## 实际验证

|作业|内容|结果|
|---|---|---|
|6853|新增测试首次运行|新runtime模块未实现导致导入失败，FAILED/1:0，原日志保留|
|6854|实现后的定向测试|7项通过，COMPLETED/0:0，1秒|
|6855|GPU真实导入登记|4196模块、7192文件、62包安装记录、8401指纹，COMPLETED/0:0，67秒|
|6856|独立GPU导入审计|8401指纹全部一致；加载4195模块/7191文件，COMPLETED/0:0，40秒|
|6857|直接执行入口--verify-imports|8401指纹全部一致；加载4195模块/7191文件，COMPLETED/0:0，41秒|

7项测试覆盖未分配GPU、Open3D使用CPU后端、缺失可见设备、合法GPU配置、检查模式不进入执行、未知参数拒绝、无授权时不创建claim。使用假对象，不运行仿真；旧28项测试和旧物理/模型实验没有重复。

独立审计与入口检查允许加载登记集合中的匹配子集，但事先核验全部8401指纹，不因模块未加载而跳过其文件。三次GPU检查均受MuJoCo构造/加载/编译及积分阻断保护，integration、model_construction、data_construction、spec_construction计数全部0。计数已写入[准备清单](evidence/remote/prepared/manifest.json)、[独立审计](evidence/remote/prepared/audit_result.json)及[实际入口检查](evidence/remote/prepared/entry_check.json)。

准备清单SHA256：66b01dbad123d36e07d55d318fa2167e28fbd89dd740650e5a373ed8dfcd37e9。准备与两次核验使用同一份冻结清单，没有在审计失败后临时补白名单。

## 归档与当前阶段

23份服务器来源、准备快照、测试/作业日志及旧claim已下载并逐份SHA256校验，见[同步清单](evidence/DELIVERY.json)。[本地档案核验器](verify_archive.py)核对旧8380项指纹全部保留、新来源、CUDA扩展、实际入口身份、资源配置、计数、日志与报告链接，结果见[最终核验](evidence/FINAL_VERIFICATION.json)。6份本轮冻结Python源码与服务器字节一致；本地verify_archive.py是后续归档工具，没有参与GPU进程。

旧v3授权哈希保持，旧v3/run仍不存在，旧v1 claim仍为1；6851仍FAILED，未重试。v4没有authorization.json、run或claim；队列为空。未修改相机、全14/85%资格、尺寸/连通性、6mm标定、3mm深度噪声/2%缺失、安全阈值和动作白名单，没有模型生成、完整抓放、训练或Git操作。

本次完成的是**场景创建前的GPU导入修复与入口核验**。尚未创建真实场景，不能保证构造/渲染/控制之后的所有延迟导入已覆盖；实际初态、MJB回放、闭合轨迹和完整抓放仍未验证，原rejected/gripper_closure保持。

下一步可基于已冻结v4另登记一次有限隔离诊断：最多500初始化步＋1000闭合步，异常/禁碰即停、失败不重试，随后一次零积分证据审计。本轮未登记或使用这项新动力学预算；单条合成轨迹即使无碰撞也不能直接解除生产门禁。

本轮使用systematic-debugging、executing-plans、定向先红后绿测试及verification-before-completion。按requesting-code-review检查项完成[串行自审](REVIEW.md)，独立审计为Slurm中的独立进程，不是子代理评审。PLAN与REVIEW保留准备时冻结版本，最终状态以本报告和CURRENT_STATUS为准。
