# 规则专家监督训练与独立评估边界

## 闭环评估收尾（覆盖下方旧进度）

闭环开发评估已完成：24份原始轨迹核验通过，微调6/6、基础3/6、规则6/6、直接重试1/6；首次失败子集微调5/5、基础2/5。3717的首次成功日志汇总异常已由独立安全后处理恢复，原始轨迹哈希不变，不能把Slurm FAILED改称COMPLETED。报告见CLOSED_LOOP_REPORT.md。当前3718已RUNNING，以expert_dual_after_loop_deploy_v1控制目录恢复双卡4worker采集；3716正常结束。test仍封存，结果不证明泛化或超越规则。


用户已明确授权另建规则专家/混合监督数据集。本次首先采集独立rule_expert版本；没有把既有LLM或混合记录并入。

## 用户授权的初步试训（已执行）

用户明确要求组会前先让模型运行，再扩大数据集。因此独立pilot允许使用当前163条train、48条validation、38条封存test；不降低下文正式实验门槛。pilot_sft_data_v1是独立冻结快照，来源rule_expert/model=null。原批次379任务中377组按原审计通过，2组无样本异常单独隔离；全部249条样本均有原始配对证据。后续恢复审计已严格重放确认这2组属于非法修正提前退出，不将其导出为样本。

作业3712已完成Qwen3.5-4B NF4/FP16 QLoRA：rank8/alpha16/dropout0.05、学习率1e-4、seed42、累积8、完整1epoch、21次更新、163样本各一次。最后批次3条，没有补齐重复。最长train1344/validation1438 tokens，最大长度4096，无截断；仅assistant答案参与loss。

48条validation的token加权loss为0.4734516→0.0000161265；496个adapter张量发生变化，保存卸载再加载后的logits最大差值0。3个预先固定开发例的changes精确匹配0/3→3/3，仅是开发演示。test未用于训练、选参或生成评估；尚无微调后物理成功率。

保存后独立作业3714完成全部48条validation自由生成：48/48包含changes的JSON，48/48参数精确匹配；单样本手工shifted CE与库loss差0。该结果仍是验证集上的规则模仿检查，不是物理成功率或独立test。训练代码和冻结数据hash收尾核对不变。

保存了optimizer/scaler/RNG/order的checkpoint，但当前入口没有resume CLI，不能宣称断点续训已验证。实际产物见pilot_sft_v1及PILOT_GROUP_MEETING.md。

## 正式实验开始条件（仍保留）

- expert_batch_v1采集停止后完成expert_audit，来源/配对/参数/物理结果均通过。
- 去重train≥1000、validation≥100、test≥100；训练中calibration/collision/placement各≥100。
- 不存在未解决worker失败；代码指纹一致；按source-destination任务组隔离，跨split输入重复为硬失败。
- 冻结三个split的文件hash和样本数；训练读取train，调参只用validation；test不用于选参、阈值修正或早停。
- tokenizer预检不得静默截断监督答案；采用与推理一致的非思考模板，仅监督assistant答案，不训练metadata。

## 训练准备

已实现全数据epoch、确定性打乱、梯度累积、独立validation损失、checkpoint保存及adapter保存后重载验证，并由上述pilot实际运行。既有8步单样本smoke仅是历史兼容检查。扩大正式训练前仍需实现并验证中断后的训练恢复入口；当前checkpoint保存不等于已实现resume。

固定随机种子、基础模型revision/hash、tokenizer、LoRA配置、优化器、学习率、最大长度和环境版本；Qwen3.5 delta-rule在V100混合精度下保留已验证的FP32保护。仅通过Slurm分配单V100，不覆盖CUDA_VISIBLE_DEVICES。

## 独立评估

相同初始场景、相同故障、最多3次尝试，对比retry、RuleReflector、未微调模型与微调模型。模型输出保留原文，禁止补写JSON或规则回退；合法率与物理成功率分开统计。训练只用通过物理成功筛选的修正，评估必须计入全部冻结任务，包括教师失败与模型无效输出，避免只评估成功样本的选择偏差。

正式测试计划在训练前冻结；不能把已有12组开发pilot称为独立测试。用于数据质量统计的heldout样本数量不等于完整任务成功率。必须区分程序规则蒸馏、LLM监督与混合监督；没有混合训练实验就不报告混合效果。

## 可声称的范围

当前是仿真几何感知、几何抓取候选与规则语言解析下的反思参数预测。标签cause继承错误信息，不是人工专家思维链。大量seed抖动不证明跨场景、新物体、真实视觉或真实机械臂泛化；最终模型是否优于规则教师须由独立实测决定。
