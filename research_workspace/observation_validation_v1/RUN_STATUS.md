# 独立种子观测聚合验证：全部完成并通过审计

24/24条件完成且资格通过，无跳过；12独立种子组、48条方法轨迹，实际93/144次独立物理执行。19个challenge、5个easy_control全部保留。

| 阶段 | 作业 | 最终状态 |
|---|---|---|
| 预检与冻结 | 5241 | COMPLETED/0:0；19项测试通过 |
| 4条件冒烟 | 5242_0—3 | 全部COMPLETED/0:0 |
| 冒烟审计 | 5243 | COMPLETED/0:0；10项篡改拒绝通过 |
| 完整24条件，复用冒烟4条 | 5244_0—3 | 全部COMPLETED/0:0；最长9分40秒 |
| 原最终审计 | 5245 | CANCELLED by 0，未启动；原因记录None，无运行日志 |
| 补跑最终CPU审计 | 5264 | COMPLETED/0:0，9秒；passed=true、complete=true |

原审计取消的具体原因未查明；保留原作业编号，jobs.json新增audit_recovery。补跑使用冻结的audit.sbatch/report.py，仅审计已有数据，没有新增仿真或修改冻结代码。全量10项真实记录篡改拒绝通过，manifest身份核验通过。

预算1：latest/median均5/24；预算2：19/24与22/24；预算3：22/24与24/24。两方法在同一首次失败状态使用相同三次合成测量，latest取最后一次、median取逐坐标中位数。不能将latest描述为只采集了一次测量。

验收时本用户队列为空，四卡显存1/1/2/5MiB、利用率均0%。本轮模型调用0、未训练、未使用最终测试。

详细结果见REPORT.md、RESULTS.md、BUDGET_CURVES.json、FAILURES.json与final_verification.json。结果是新训练候选条件上的小规模开发验证，不作统计显著或模型收益声明。
