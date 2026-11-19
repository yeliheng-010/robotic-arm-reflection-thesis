# 明日验收入口

服务器目录：`/home/yeliheng/grasp_server/framework_ablation_v1`。

协调器作业5176在服务器Slurm内运行。本地电脑、浏览器、Jupyter终端断开均不承担调度功能。29项CPU预检5175通过，冻结480条目、60开发条件、527个来源身份。冻结清单SHA256：`bdd3258f51c573dad79dbb33355fa4caadabc667c7f3c2ebbb3ef3a2a32c80fd`。预检5174的旧组名断言失败保留，正式实验从5175预检通过后开始。

## 自动执行顺序
1. 启动模型，核验adapter切换重载误差及9次旧开发文本回放；正式实验只使用禁用adapter的基础4B。
2. 三仿真分片执行48条冒烟，逐条物理审计；门禁另做20项真实记录篡改拒绝检查。
3. 审计通过后执行预算3的全部240条，复用冒烟48条；生成PRIMARY_REPORT.md、primary_verification.json。
4. 主实验审计通过后执行预算4的240条；生成FINAL_REPORT.md、verification.json，检查前三次尝试前缀。
5. 服务自动停止，GPU随Slurm作业结束释放；STATUS.json写入completed或failed。

## 验收标准
- `STATUS.json`为completed；`verification.json`的passed和complete都为true，accounted=expected=480。
- 四组每预算各60条；记录失败、无效输出和跳过，禁止只统计成功样本。
- jobs.json全部正式作业退出码0:0，service/process_exit.json退出正常；未修改其他用户作业。
- primary与final指标分开查看；历史消融只改变模型history字段，共享候选不读取历史。
- `budget_prefixes.tasks`应为240，物理/噪声/候选配对审计通过。
- `service/stopped.json`存在；若失败，查看STATUS.json、对应审计失败JSON、controller/model/worker日志，禁止直接覆盖同目录重跑。

## 明日分析顺序
先比较retry→rule及retry→current/history，判断反馈闭环是否有效；再比较current→history，判断历史信息是否有增益；最后比较同一方法预算3→4，判断多步恢复是否受预算限制。不得把提高预算归因为微调。现有种子均开发用途，不作最终盲测或独立60种子显著性证据。

若全组表现接近，应保留结果，进一步检查任务是否需要历史、反馈是否过于理想，以及规则候选已承担多少推理。后续显式重观测、训练补采、单答案/多答案受控微调仍需基于结果推进；本轮没有启动这些部分。

查看状态命令：
```bash
cat /home/yeliheng/grasp_server/framework_ablation_v1/STATUS.json
cat /home/yeliheng/grasp_server/framework_ablation_v1/jobs.json
cat /home/yeliheng/grasp_server/framework_ablation_v1/REPORT.md
squeue -u yeliheng
```
