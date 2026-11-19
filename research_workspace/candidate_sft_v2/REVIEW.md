# 验证与执行边界

采用串行自审，未声称独立子代理审查。使用轻量executing-plans、关键损失test-driven-development、systematic-debugging与verification-before-completion。

- 关键后缀损失测试先因实现缺失失败，随后与全序列masked交叉熵及梯度等价验证通过；另有无监督/非连续标签拒绝、重复JSON键/未知候选/额外字段拒绝和尾批7条覆盖测试，共7项通过。
- 实际tokenizer验证159/49/29全部消息前缀及assistant mask，不截断。数据manifest与每个split/index文件哈希校验，原训练/开发划分不改，原最终测试未读。
- v1首次forward OOM保留为5068 FAILED/1:0。按实际栈追踪到SDPA GQA分支；v2显式重复KV且禁用math/Flash回退，未修改系统依赖、原研究协议或其他用户进程。
- 5070在V100实测高效SDPA前向/梯度误差通过预设FP16容差；9439-token最长训练样本更新成功；独立进程重载logits误差0。
- 正式训练重新调用setup从基础权重初始化，smoke adapter不作训练起点；20个累积组覆盖159条恰好一次，末批7条；每步检查有限loss、非零有限梯度、AMP无跳步，定期保存checkpoint。
- 前后评估使用同一4B基础权重、NF4/FP16、SDPA、提示、max_new_tokens128与greedy解码；before显式disable_adapter，after校验保存文件哈希并独立重载比较logits；仅adapter不同。
- 自动报告必须两个方向均覆盖全部49+29索引且来源ID匹配，才生成passed=true；失败输出单独verification_failure.json，不以Slurm退出或低loss替代模型效果。
- 调度主机内存预留初始过高阻塞并行，按实测MaxRSS调低尚未运行的评估项，运行中项保持不变，未绕过Slurm。
- 完整训练、after评估与60开发条件物理闭环尚未完成；当前成果为已验证并启动的训练/离线评估执行链。
