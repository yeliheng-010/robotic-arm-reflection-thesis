# 候选选择器 Qwen3.5-4B 一轮微调

恢复版本v2：原candidate_sft_v1作业5068在最长9439-token样本第一次forward时OOM，未产生有效梯度更新、未启动正式训练。保留原冻结代码/manifest/日志。根因线索为transformers SDPA传enable_gqa=True，PyTorch2.6在V100无法用Flash且高效内核不支持该GQA路径，回退math生成5.31GiB注意力矩阵。v2显式调用原repeat_kv分支并只允许EFFICIENT_ATTENTION；GPU先测与math GQA的前向及梯度一致性。数据、完整输入、预算和学习超参不变，后继独立结果目录。

用户已明确选择：Flash-Next保留作教师/推理基线，Qwen3.5-4B作为学生微调。Flash本地仅有qwen4exp/IQ3_S GGUF，两分片共83,617,662,656字节、约176.94B张量元素；当前transformers5.20.1配置映射不支持qwen4exp。四张V100各16GiB当前空闲。不得将学生训练描述为Flash本体训练。

目标：159条保守单标签样本、1epoch、有效batch8、rank8、lr1e-4、seed42，实际20次更新（末批7条）。49条开发诊断做同基础权重、同量化、同提示和解码的前后对照，29条旧场景单独诊断。预留测试封存，原模型/adapter及冻结实验不覆盖。

边界：仅新增本目录；复用已验证的4B模型加载和稳定性设置，独立读取本轮混合来源数据，不能直接调用旧rule-only数据入口。原模型权重、代码、数据和tokenizer哈希冻结。GPU工作全部经Slurm。

风险：长输入的全词表logits会浪费显存；使用仅覆盖assistant监督后缀的logits计算损失，并与全序列masked cross entropy验证loss及梯度一致。保留全部prompt token、不截断、不删长样本。微批1、梯度累积8、FP16/NF4与梯度checkpoint。

执行状态：
- [x] CPU预检：模型身份/文件哈希、全部输入token长度、模板前缀、assistant mask、候选目标、划分索引。
- [x] 定向测试：后缀损失/梯度等价、无监督与非连续标签拒绝、尾批覆盖、严格JSON生成评价。
- [x] GPU冒烟：最长训练样本真实更新、非零有限梯度、adapter变化、独立进程重载及输出对齐；预估时长/显存。
- [ ] 前测与正式训练：未微调4B分片生成验证，训练独立从基础权重开始1epoch；冒烟adapter不继续计入正式训练。
- [ ] 后测与审核：保存重载，完整49条开发诊断前后对照和29条旧场景，冻结结果及哈希。

完成训练后再根据生成合法性进入已规划60个开发条件的物理闭环；不得将标签命中率当作物理成功率，也不得声称超过教师或规则。

流程：executing-plans（串行轻量执行）、test-driven-development（损失/边界）、verification-before-completion。无Git远程操作。

执行记录：7项定向测试通过；5070最长9439-token样本更新496个adapter张量，峰值13.05GiB；高效SDPA前向/梯度与math GQA对比通过，独立进程重载logits误差0。正式5071正在运行，共20次更新；5072三分片做未微调对照，5073等待正式训练完成后评估，5074最终审计。实时进度及资源调整见RUN_STATUS.md，不把冒烟更新计入159条正式epoch。
