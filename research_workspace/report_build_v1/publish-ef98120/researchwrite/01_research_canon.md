# 事实与术语边界

1. 现有系统使用 MuJoCo 物理仿真；simulation 感知提供仿真位置和掩码，不能当作完整视觉链路性能。来源：服务器《机械臂项目任务说明》“无头运行”节。
2. 已完成 Qwen3.5-4B 的规则监督文本 QLoRA：163 条训练数据、1 epoch、21 次更新。来源：evidence/pilot/result.json 与 manifest.json。
3. 48 条验证生成的参数均匹配规则标签。来源：evidence/pilot/validation_generation.json；不是最终测试结论。
4. 6 个开发场景中 adapted 6/6、base 3/6、rule 6/6、retry 1/6。来源：evidence/closed_loop/result.json。
5. 闭环原作业 3717 FAILED，后处理恢复汇总，24 份原始物理结果保持不变。来源：completion_recovery.json 与 delivery_verification.json。
6. supervision_source=rule_expert，model=null；不能称为纯模型自举、人工思维链或多模态微调。
7. 持续故障：calibration、collision、placement。历史 planning/grounding 注入会在重试时自然消失，必须单独对照。
8. 实验单位：独立场景实例；重试属于同一实例；同一任务族多个种子存在相关性。
9. 用户要求先完成初步微调，再扩充数据；正式扩量门槛仍为 train≥1000、validation/test≥100、训练每类故障≥100。
10. 作者已提供题目《基于机械臂的错误反馈于智能反思系统》，原文保留。未提供导师原始开题要求，不能将本实验计划称为导师已批准方案。

文献事实：本轮未开展系统检索，不引入未经核验的文献结论。后续须核验反思、机器人失败恢复、规则蒸馏、参数高效微调相关工作。

禁止主张：已优于规则、已统计显著、已真实机械臂验证、已跨物体泛化、已端到端视觉微调、48 条基线生成从 0/48 提升。
