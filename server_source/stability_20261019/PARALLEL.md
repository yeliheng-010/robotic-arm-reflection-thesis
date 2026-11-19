# 多GPU采集调度

## 闭环评估收尾（覆盖下方旧进度）

闭环开发评估已完成：24份原始轨迹核验通过，微调6/6、基础3/6、规则6/6、直接重试1/6；首次失败子集微调5/5、基础2/5。3717的首次成功日志汇总异常已由独立安全后处理恢复，原始轨迹哈希不变，不能把Slurm FAILED改称COMPLETED。报告见CLOSED_LOOP_REPORT.md。当前3718已RUNNING，以expert_dual_after_loop_deploy_v1控制目录恢复双卡4worker采集；3716正常结束。test仍封存，结果不证明泛化或超越规则。


最新资源选择：用户再次明确要求四卡。local-llm.service现已真正停止并禁用，GPU0/1显存清空；剩余阻塞仅为root的llm-hold作业3414/3630保留Slurm配额。当前双卡3688继续采集，不中断等待；管理员释放占位后再做四卡真实验证及迁移。此前仅用双卡决定已被本次要求覆盖。

最新状态：双卡验证3686正常完成0:0；4任务原始审计通过，与原单卡任务参数、物理结果、监督文本完全一致。13项测试与4文件结构检查通过。原批次3685正常停止于35任务/24样本，105个原始结果和summary文件已记录hash，STOP迁移标记归档。双卡正式作业3688运行，GPU2/3各2个仿真进程；控制目录expert_parallel_batch_deploy_v1，数据仍写expert_batch_v1。

四卡尝试：用户释放资源后曾实测4卡显存均0；随后local-llm.service自动重启strata（PID1372555）占用0/1。Slurm隐藏队列中的root llm-hold作业3414/3630仍保留两个gpu:svc。四卡smoke3687因Resources未启动，已取消，不能报告四卡验证通过。管理员需要同时停止local-llm.service并确认释放这两个占位作业；仅杀进程不足以使四卡可调度。

以下为方案与早期过程说明，当前资源与作业以上述状态及实时squeue -a为准。

用户已允许使用四张显卡，并明确允许尝试停止占用GPU0/1的local-llm/strata。实际TERM操作返回Operation not permitted，未停止该系统服务。当前仅GPU2/3可用；Slurm区分gpu:svc:2与gpu:v100:2，因此本轮使用两张v100。四卡逻辑尚未实际验收，不能报告四卡运行。

调度器保持原expert_batch_v1/manifest.json和全部物理/导出代码不变；新增parallel_state/parallel_lane/parallel_collect，单独保存部署身份。原manifest的workers=2描述已冻结单lane基线；新部署明确每GPU两个worker及总GPU数。

主进程持有原批次.collector.lock，独占写status/dataset；每个Slurm步骤只分配一张卡，每lane两个进程。按原任务编号对GPU数取模分片；已完成summary跳过，半成品保留并通过既有worker恢复。任务计划、seed、分组、规则来源及质量门槛完全复用。

暂停迁移时用原STOP让在途结束并审计；STOP归档保留后才恢复。HALT由主进程单独写入，worker失败会非零退出并触发其他lane停止接收新任务。数量达标、用户STOP、质量失败、代码漂移均停止新增任务，在途结束后统一审计。失败部署不直接复用HALT目录，必须查清原因并创建新部署身份。

部署命令：先用parallel_collect --freeze冻结独立部署，再通过expert_parallel.sbatch运行。两个GPU的脚本默认gres=gpu:v100:2、16CPU、32GB内存；各step申请8CPU/12GB/1GPU，不覆盖CUDA_VISIBLE_DEVICES。控制目录runtime.json与lane_N.json记录Slurm job、GPU可见编号及任务编号；实际物理卡以scontrol/nvidia-smi核验。

验证：4项分片/去重/非法lane/恢复测试先失败后通过，连同既有专家测试13项通过；4个新文件结构检查符合函数≤50行、文件≤300行、位置参数≤3。真实双卡smoke为独立expert_parallel_smoke_v1的前4任务，不混入正式数据集。完成后对比原同任务输出，并检查原批次数据原件未变。

GPU0/1后续需由有权限的管理员释放系统服务；释放后重新检查占用、更新资源部署并做四卡真实验收，再扩展。没有申请sudo或修改系统服务配置。
本文件下文为旧调度历史。当前改用每任务独立子进程、24GB/lane与expert_recovery.sbatch（双卡总64GB）；smoke3713通过，3715已实际恢复双卡4worker采集。旧3688已因12GB step内存上限失败；不要按旧脚本重启。当前命令与恢复证据见RUNBOOK.md，初步微调结果见PILOT_GROUP_MEETING.md。
