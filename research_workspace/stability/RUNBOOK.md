# 专家批次查看与恢复

## 闭环评估收尾（覆盖下方旧进度）

闭环开发评估已完成：24份原始轨迹核验通过，微调6/6、基础3/6、规则6/6、直接重试1/6；首次失败子集微调5/5、基础2/5。3717的首次成功日志汇总异常已由独立安全后处理恢复，原始轨迹哈希不变，不能把Slurm FAILED改称COMPLETED。报告见CLOSED_LOOP_REPORT.md。当前3718已RUNNING，以expert_dual_after_loop_deploy_v1控制目录恢复双卡4worker采集；3716正常结束。test仍封存，结果不证明泛化或超越规则。


## 当前阶段：单卡采集与闭环开发评估并行

用户已采纳先验证实际任务效果的建议。旧双卡3715正常收尾于404任务/264样本；当前单卡采集3716（expert_single_collect_deploy_v1）持续扩量。另一张卡上3717运行6个新场景×retry/rule/base/adapted的24次完整闭环执行，seed40000、validation任务组、最多3尝试，test继续封存。模型与提示固定，不按结果修改重跑。当前初步训练结果保持有效，但完整闭环结论尚待24次执行和原始审计完成。详见CLOSED_LOOP_PLAN.md。



## 当前入口：pilot已完成，双卡恢复版本

根目录：/home/yeliheng/grasp_server/stability_20261019。训练结果pilot_sft_v1/result.json；模型pilot_sft_v1/adapter；固定数据pilot_sft_data_v1。3712已完成；3714全部48条validation自由生成完成，48/48修正参数匹配；3715已实际RUNNING并恢复双卡扩量（控制目录expert_recovery_batch_deploy_v1）。不要重复运行sft_train或重写pilot目录。

查看命令：

```bash
squeue -u yeliheng
sacct -j 3712,3713,3714,3715 --format=JobID,State,ExitCode,Elapsed,MaxRSS
cat /home/yeliheng/grasp_server/stability_20261019/pilot_sft_v1/result.json
cat /home/yeliheng/grasp_server/stability_20261019/expert_batch_v1/status.json
cat /home/yeliheng/grasp_server/stability_20261019/expert_recovery_batch_deploy_v1/runtime.json
```

新调度仅通过expert_recovery.sbatch申请双v100/64GB，step24GB，每GPU2个线程分别启动独立仿真子进程。不要使用下方历史12GB step调度。当前四卡尚未验收且svc配额仍受root占位，不提交旧四卡脚本。

旧3688的状态保存在expert_batch_v1/status_before_recovery_3713.json，旧源码在source-parallel-before-recovery.json，旧HALT保留。恢复需新deployment及recovery_admission.json，绑定旧状态hash、新smoke成功证据和调度身份。启动时仍检查独占锁、STOP、代码身份；不能直接擦除worker_failures。

recovery_audit在新增的recovery_audit.json保存审计，保留旧expert_audit.py身份。提前失败仅在规则异常可重放、retry完整、来源和轨迹严格一致且没有导出样本时接受为失败。收集期间不得运行会改写status/dataset的全量audit。STOP仍用于等待在途正常退出。

批次status中的training_started=false是原完整批次正式训练标志，不代表独立pilot未运行；pilot是否完成以pilot_sft_v1/result.json为准。pilot不自动替代正式数量门槛或闭环评估。checkpoint含训练状态，但没有resume CLI。

## 历史操作记录（不作为当前启动命令）



用户最新决定：再次要求四卡提高效率。服务已inactive/disabled且GPU0/1显存清空；仍需管理员确认后取消root占位3414/3630，释放Slurm配额。当前双卡3688继续运行；释放后按独立四卡smoke、审计、平滑迁移顺序执行，不绕过Slurm。此前仅用双卡要求已被覆盖。

根目录：/home/yeliheng/grasp_server/stability_20261019。

当前采集：expert_batch_v1，作业3688，控制目录expert_parallel_batch_deploy_v1。GPU2/3每卡2worker，共4worker。原任务池5700、物理代码及导出身份保持冻结。原3685于35任务/24样本时正常停止并审计；105个结果/summary原件hash存migration_parallel_before.json，STOP归档为STOP.migration_parallel_archived。

```bash
squeue -a -o "%.12i %.15u %.24j %.10T %.24b"
sacct -j 3685,3686,3687,3688 --format=JobID,State,ExitCode,Elapsed
cat /home/yeliheng/grasp_server/stability_20261019/expert_batch_v1/status.json
cat /home/yeliheng/grasp_server/stability_20261019/expert_parallel_batch_deploy_v1/runtime.json
tail -n 20 /home/yeliheng/grasp_server/stability_20261019/expert_parallel_batch_deploy_v1/lane_0.log
tail -n 20 /home/yeliheng/grasp_server/stability_20261019/expert_parallel_batch_deploy_v1/lane_1.log
```

旧expert_batch_v1/runtime.json属于原单卡作业3685；当前GPU映射必须查看控制目录runtime和lane文件，并以scontrol/nvidia-smi交叉核验。

正常停止：在expert_batch_v1下创建STOP，等待在途完成。不要直接启动旧expert_collect或同批第二个collector。恢复前确认旧作业结束、检查stop_reason及worker_failures，解决失败/停止意图并保留旧STOP。每次失败或停止后创建新的expert_前缀deployment目录，冻结调度代码身份。数据目录始终expert_batch_v1；完整summary和子运行复用，中断结果保留。

```bash
cd /home/yeliheng/grasp_server/improvement_20261019/code
# 以下示例deployment名称仅在不存在时使用；更改运行标识后再执行
# 使用既有env_sim Python及PYTHONPATH、三项线程=1环境：
# python -m stability.parallel_collect --run expert_batch_v1 --deployment expert_parallel_batch_deploy_v2 --gpus 2 --freeze
# sbatch /home/yeliheng/grasp_server/stability_20261019/expert_parallel.sbatch --run expert_batch_v1 --deployment expert_parallel_batch_deploy_v2 --gpus 2
```

数量门槛：去重train1000、validation100、test100；训练三类持续故障各100。达到后停止新增任务，等待在途结束并自动完整审计，不自动训练。采集期间不要运行会改写status/dataset的全量audit；只读检查单任务可使用audit_task。

四卡前提：GPU0/1受local-llm.service和root的llm-hold 3414/3630双重占用。用户已授权使用四卡，但当前账号TERM返回Operation not permitted；服务曾被释放后自动重启。请管理员同时处理服务与占位。之后重新确认squeue -a/nvidia-smi，再先提交expert_four.sbatch对独立smoke验证（gres=svc2+v1002，32CPU，64GB），通过后迁移正式采集。3687仅排队后取消，绝不能记作四卡已验证。

专家门禁expert_gate.json源于expert_pilot_v2；纯模型pilot_gate仍false。独立双卡smoke3686不混入训练数据。正式训练入口尚需实现，先完成数量、来源、去重、分组、物理证据审计，见TRAINING_PROTOCOL.md。
