---
date: 2026-11-18
status: failed_before_claim_cpu_gpu_import_mismatch_archived
diagnostic_claim_consumed: 0
execution_submissions: 1
setup_steps: 0
task_steps: 0
saved_runtime_counters: false
evidence_audit_consumed: 1
dynamics_validated: false
---

# v3单次诊断在claim前被GPU导入差异拒绝

用户已确认最多500初始化步、1000闭合步的一次隔离诊断及一次零积分证据审计。6850完成预算登记；6851唯一执行作业在受保护导入核验中失败，未创建claim或场景；6852完成失败证据审计。**初始化和闭合均未进入，没有动力学结果；本次不重试。** 原生产rejected/gripper_closure保持。

## 失败与根因证据

[6851日志](evidence/remote/execute-6851.log)停在entry.preclaim→validate_runtime：Open3D的cuda/pybind扩展没有被准备清单登记。失败早于consume和run_environment，服务器v3/run不存在；[审计](evidence/remote/failure_audit.json)核验冻结AST中的顺序与导入保护范围。步数为0依据控制流和异常位置，**没有保存6851运行计数器，不能称已读取到零计数日志**。

[资源分配记录](evidence/remote/job_status.txt)显示6848准备、6849导入审计均未分配GPU，6851实际分配了GPU。原准备快照登记open3d.cpu.pybind；冻结的[Open3D导入选择源码](evidence/remote/dependency/open3d_init.py)在CUDA设备数大于0时导入open3d.cuda.pybind。这解释了CPU准备通过而GPU执行拒绝：准备环境未覆盖实际执行资源下的导入分支。

6852再次核验全部8380项冻结指纹。新增被拒绝二进制属于Open3D 0.19.0，与当前安装RECORD匹配，SHA256为36ba0fadf9f92aa6c1ac66d5d1c46f7ce13957cc497658c1d29580e695cbc986。它此前不在运行文件清单或授权identities中；本轮事后哈希不追溯成为旧授权已绑定的来源，也不豁免来源门禁。

## 预算、结果与审计边界

|作业|内容|结果|耗时|
|---|---|---|---|
|6850|核验8380项来源，独立登记预算|COMPLETED / 0:0|24秒|
|6851|唯一v3执行提交|FAILED / 1:0，claim前拒绝|37秒|
|6852|零积分失败证据审计|COMPLETED / 0:0|27秒|

授权已登记，执行已提交一次；新轨迹claim消耗0、证据审计消耗1。未消耗claim不代表允许自动重提；“失败不重试”仍适用。[独立授权](evidence/remote/engine/authorization.json)及原失败完整保留，旧6832 claim仍为1。没有模型生成、完整抓放或训练，未重复旧实验或28项已完成测试。

没有MJB、轨迹或完成结果，因此没有调用正常轨迹审计。6852只读授权、失败日志、资源记录、源代码、准备清单和当前安装信息；未导入MuJoCo、Open3D或grasp_process，不创建场景、不积分。审计通过表示失败证据一致，**不表示动力学通过或CPU/GPU运行兼容性已经修复**。

本地audit.py/audit.sbatch是准备过但未上传、未运行的正常轨迹适配草案；实际唯一审计入口为[failure_audit.py](failure_audit.py)。冻结PLAN保留登记时文本，完成状态以本报告和CURRENT_STATUS为准。不得运行本目录execute.sbatch重试。

## 归档、核验与下一步

21份来源、授权、日志、状态及旧claim证据已下载并逐份SHA256校验，见[同步清单](evidence/DELIVERY.json)。本地[档案核验器](verify_archive.py)核对下载文件、注册绑定、14份冻结v3 Python源码、旧claim、失败状态和报告链接；结果见[最终核验](evidence/FINAL_VERIFICATION.json)。服务器队列为空。代码review为串行自审，独立审计是Slurm中的独立进程，没有使用子代理。

当前仍是闭合安全诊断的工程阻塞阶段，实际合成初态、闭合轨迹及完整抓放均未得到新验证。下一步建议新版本在与执行相同的GPU资源条件下，先完成**禁止场景构造和积分的真实导入登记、独立审计及执行入口核验**，覆盖CPU/CUDA选择和其他延迟导入；不能只补当前一个二进制便假定所有差异已消除。通过后再考虑新的有限动力学预算。本轮未修改冻结引擎、未启动该新版本或新轨迹。

采用executing-plans、systematic-debugging、verification-before-completion，并按requesting-code-review检查项串行自审。未执行Git操作。
