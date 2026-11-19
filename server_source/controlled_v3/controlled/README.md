# 受控噪声实验：请求审计修复版

## 修复内容

v2 的实际模型请求将当前反馈转换成 ErrorReport 后序列化；审计却直接序列化投影字典。两者字段内容相同，但 `stage` 等键的插入顺序不同，导致字符串比较失败。

本版仅修改 audit_request：按实际发送路径构造 ErrorReport 再生成预期请求，历史保持原来实际展示的投影。继续逐字核对完整消息，不放宽参数、测量、历史、系统提示和预算校验。

除发布目录路径调整与新增测试外，生产逻辑只有 audit.py 变化。提示词、场景、噪声、任务矩阵、模型预算和物理成功判据未修改；场景协议仍为 controlled-noise-v2。
旧 controlled_v2 的 160 个冻结文件指纹已确认未变；旧失败结果未改写。

## 验证证据

- 修复前：新增 4 项回归测试均重现同一个请求审计断言失败。
- 修复后：新增和原有共 13 项测试通过。
- 覆盖真实失败归档、双轮反思历史，以及测量值、参数、历史内容、字段缺失、角色、系统提示和 token 预算篡改。
- 旧版三方法 smoke 重新审计通过：初态配对、展示反馈和执行参数均核验通过。旧版结果仍保留 failed 状态，本次只另存复核证据。
- 相关记录在 evidence/tests.log、evidence/regression_before.log、evidence/archive_reaudit.json。

## 新实验

Slurm 流水线：4698 重新预检 48 场景 →4699 重跑真实三方法 smoke → 同作业启动 144 次正式开发任务。
任一前置检查失败则停止后续执行；模型服务中断仍保留已完成任务并停止批量。

已验证：4698 完成，48/48 通过；4699 的 smoke 已完成且 verification_passed=true，现已进入 pilot（144 次任务）。
本次 smoke：直接重试三次失败；规则第二次成功；Flash 两次合法修正、三次执行后失败，服务错误 0。
该结果与旧版 Flash 单场景成功不同，已原样保留；审计通过仅说明请求、反馈和实际执行一致，不代表模型纠错成功。

```bash
squeue -j 4698,4699
sacct -j 4698,4699 --format=JobID,State,ExitCode,Elapsed
```

本版输出：`/home/yeliheng/grasp_server/controlled_v3`。不要重复提交到同一个输出目录。
最新完成度见 evidence/server_status.json；提交和启动不等于完成整批实验。
本次不启动微调、不扩展到 192 条件，也未推送 GitHub。
