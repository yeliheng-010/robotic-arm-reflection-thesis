# 主张与证据

| 编号 | 主张 | 证据 | 强度/状态 | 用途与限制 |
|---|---|---|---|---|
| E1 | 初步微调已运行完成 | evidence/pilot/result.json、manifest.json | evidence-backed | 工程流程可行性，不代表正式实验完成 |
| E2 | 保存后验证参数匹配 48/48 | evidence/pilot/validation_generation.json | evidence-backed | 规则模仿；没有全量未微调生成基线 |
| E3 | 6 场景闭环 adapted 6/6，base 3/6 | evidence/closed_loop/result.json | evidence-backed | 小规模开发结果，不能推断泛化 |
| E4 | 与规则持平 | 同 E3 | evidence-backed | 此批 6/6 对 6/6，不等于总体等效 |
| E5 | 24 份物理轨迹未因汇总修复改变 | evidence/closed_loop/completion_recovery.json、delivery_verification.json | evidence-backed | 原 Slurm FAILED 必须保留 |
| E6 | 采集继续推进 | evidence/status_snapshot.json、server_check.txt | evidence-backed | 时间快照，持续变化 |
| H1 | 扩大多样性提高新场景恢复能力 | 尚无独立大规模测试 | hypothesis | 由 E2/E3/E4 实验编号验证，不能写为结果 |
| H2 | 结构化证据比仅错误文本有效 | 尚无单变量消融 | hypothesis | 模型和提示共同变化的历史实验不足以归因 |
| H3 | 真实视觉与混合监督可能扩展能力 | 尚未执行 | hypothesis | 扩展路线，不纳入当前完成度 |
| U1 | 方法优于规则或已有工作 | 无 | unsupported | 不作结论；需要新证据与文献核验 |
