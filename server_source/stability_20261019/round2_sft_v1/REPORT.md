# 第二轮微调与全量验证结果

第二轮 Qwen3.5-4B QLoRA 已完成，训练及四个生成验证作业全部 `COMPLETED / 0:0`。独立交付核验脚本退出码为 0，`delivery_verification.json` 中 `passed=true`。本轮没有执行机械臂闭环或封存测试。

## 数据与训练

采集作业 3718 执行 2345 个任务后达到样本门槛，停止新增任务；并非完成原计划全部 5700 个任务。2345 条任务轨迹经来源复核，得到 1512 条合格规则监督样本，冻结为 train1002 / validation294 / test216。来源为 `rule_expert`、`model=null`，不是纯模型自主反思或人工思维链。

训练从 Qwen3.5-4B 基础模型重新开始，没有续训旧 pilot adapter。配置为 NF4/FP16 QLoRA、rank8、alpha16、dropout0.05、学习率1e-4、seed42、1epoch、梯度累积8、最大4096 tokens；只计算 assistant 答案的监督损失，无截断。

| 检查项 | 已验证结果 |
|---|---|
| 训练作业 | 3901，33分08秒，成功退出 |
| 样本覆盖 | 1002条各使用一次，126次有效更新，尾批2条 |
| 恢复训练 | 第1步保存后退出，在新进程恢复 optimizer、scaler、RNG、adapter及顺序，完成剩余125步 |
| 可训练参数 | 16,232,448 |
| 变化的adapter张量 | 496 |
| 全量验证loss | 0.4665320020 → 0.0000556252，同294条、18234个监督token |
| 保存重载 | 检查样本的logits最大绝对差值0 |
| PyTorch显存分配峰值 | 12,096,673,792 bytes，约11.27 GiB，不等于nvidia-smi进程占用 |

训练集包含594种不同参数修正和8个物体—目标组合；验证集包含229种修正和另外2个组合。分组与提示哈希跨split无交集。测试文件仅用于身份、来源与分组完整性审计，没有输入模型。

## 全量自由生成对照

基础模型与保存后的新adapter均使用同一NF4基础权重、相同294条validation、相同提示、关闭thinking、greedy解码和256个新token上限。每个方法两个分片，各147条；最终逐索引核对覆盖、任务身份、故障类型、期望标签及adapter哈希，重新解析原始输出计算指标。

| 指标 | 基础模型 | 第二轮adapter |
|---|---:|---:|
| 包含changes字典的JSON | 294/294 | 294/294 |
| changes参数严格完全匹配 | 0/294 | 294/294 |
| calibration完全匹配 | 0/129 | 129/129 |
| collision完全匹配 | 0/66 | 66/66 |
| placement完全匹配 | 0/99 | 99/99 |

基础模型作业3902/3903分别耗时23分18秒、19分50秒；adapter作业3904/3905分别耗时20分29秒、26分07秒。两组验证均为独立进程加载；所有分片的手工移位交叉熵与库loss差值为0。

`JSON`列只检查可解析对象和`changes`字典，不代表完整参数合法性。`完全匹配`比较全部参数键及数值，不比较cause文本；严格数值不匹配也不必然代表物理任务失败。基础模型抽查中出现漏改偏移轴、放置修正方向错误、碰撞场景改错参数等现象。

这些结果证明该adapter能在当前验证分布上复现规则参数修正。输入包含仿真ground-truth残差等观测，任务族和监督方式仍有限；不证明100%的机械臂成功率、独立推理能力、跨分布泛化或真机效果。不能将本轮loss与旧pilot在不同验证集上的loss直接比较。

## 下一步

暂不继续增加训练轮数：当前规则标签匹配已饱和。优先以新adapter做仿真闭环配对对照，比较retry、rule、base、round2，固定场景、种子和尝试预算，统计成功率、无效修正、尝试次数及耗时。完成开发评估后冻结协议，再使用封存任务做最终测试；必要时补充新扰动、多故障组合和证据消融。

Qwen3.8-Flash-Next的原版与量化部署条件见[可行性报告](QWEN38_FEASIBILITY.md)。本次仅完成元数据、机器和运行库检查，尚未下载其权重或执行推理。

## 产物与复查

- 服务器adapter：`/home/yeliheng/grasp_server/stability_20261019/round2_sft_v1/adapter`
- adapter权重SHA256：`0077f2d2d2c8cf171321c5c191dfa585ad16881bc27282617ac40dc5937be5a7`
- 服务器完整输出：同目录的`result.json`、`validation_base_all.json`、`validation_adapted_all.json`、`delivery_verification.json`、`slurm_final.txt`、`verification.log`。
- 本地摘要证据：[训练结果](result.json)、[冻结配置](manifest.json)、[最终核验](delivery_verification.json)、[作业状态](slurm_final.txt)、[标签多样性](label_diversity.json)。本地JSON为读取后保存的副本，远端冻结文件是哈希核验对象。
- 新增恢复逻辑采用test-driven-development；2项checkpoint测试与3项既有SFT数据测试共5项通过。交付采用verification-before-completion，最终核验通过后再报告完成。
- 收尾检查：用户作业队列为空，GPU0–3显存均为0 MiB。四卡曾由独立smoke3900验证分配和计算成功；本轮是单卡训练加独立验证分片，不是四卡DDP训练。

