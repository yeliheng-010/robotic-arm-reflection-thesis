# 单卡 V100 的 7B QLoRA 实测

北京时间 2026-10-19 00:56:58—00:57:29，服务器 Slurm 作业 **3608**，状态 `COMPLETED`、退出码 `0:0`。一张 `gpu:v100`，其余卡未申请；完成后 GPU 2/3 均回到空闲状态。现有 GPU 0/1 服务保持原有显存占用。

| 项目 | 实测或配置 |
| --- | --- |
| 模型 | Qwen/Qwen2.5-7B-Instruct |
| GPU | Tesla V100-SXM2-16GB，sm_70 |
| 软件 | Python 3.11.17；torch 2.5.1+cu121；transformers 4.48.3；peft 0.14.0；accelerate 1.3.0；bitsandbytes 0.45.2 |
| 量化/计算 | NF4 4bit + double quantization；FP16；SDPA；梯度检查点 |
| LoRA | rank 8，alpha 16，dropout 0.05，七类线性投影 |
| 可训练参数 | 20,185,088 |
| 数据 | 1 条已验证修正，实际 326 token，其中 35 token 参与监督 |
| 长度/批次 | 长度上限 512；微批次 1；累积 2；有效批次 2（本次为重复样本） |
| 训练 | AdamW，学习率 1e-4，8 个成功更新步 |
| 更新部分耗时 | 11.50 秒 |
| 进程总耗时 | 31.04 秒，含加载、保存、重载和生成 |
| PyTorch 峰值已分配显存 | 9,943,323,136 字节，9.260GiB |
| PyTorch 峰值预留显存 | 10,420,748,288 字节，9.705GiB |
| 首样本测量损失 | 2.94770 → 0.00922，仅训练集记忆检查 |
| 更新验证 | 梯度有限且非零；392 个 adapter tensor 改变 |
| 保存重载验证 | 最后位置 logits 最大差 0.0 |
| 生成 | 训练输入上生成有效 JSON，复现该条修正 |
| adapter 权重大小 | 80,792,096 字节，约 77.05MiB，不含 tokenizer |

显存是训练阶段的 PyTorch 统计，不包含所有 CUDA 上下文开销，也不是完整 512 token 输入或更长上下文的实测。本次只验证单卡；双卡/四卡训练尚未实现或测试。

## 文件与复现

服务器：

```text
/home/yeliheng/grasp_qlora/env/
/home/yeliheng/grasp_qlora/models/Qwen2.5-7B-Instruct/
/home/yeliheng/grasp_qlora/data/train.jsonl
/home/yeliheng/grasp_qlora/runs/smoke/smoke_result.json
/home/yeliheng/grasp_qlora/runs/smoke/adapter/
/home/yeliheng/grasp_qlora/smoke.log
```

本地原始结果与调度记录：`logs/reflection/qlora_smoke_v100_20261019/`。数据清单：`logs/reflection/qlora_bootstrap_dataset/dataset_manifest.json`。具体新目录复跑命令见 [README.md](README.md)。

- 数据 SHA256：`958c27f35d81efb504875a7f351db9dfb59fe611affc0eb7799b2fd93995248b`
- 训练脚本 SHA256：`c06d224e7ebf9443407eff6cbe3e4bd5b2856a3a35993f94f92695503bccafc5`
- adapter 权重 SHA256：`303e0576582329b11308b5ba4adcc8e43bb05ea942ac56917bd3a5804c53fecc`

本地数据导出/编码测试 3 项通过；shell 语法、Python 语法检查通过。运行日志中的 temperature/top_p/top_k 警告来自基座默认生成配置；本次使用确定性生成，这些采样设置未参与生成。

## 结果边界

这次证明服务器可以运行上述配置的 **7B QLoRA 训练、保存和加载**。单条样本反复训练后的损失和生成不能说明泛化能力，也不能说明机械臂故障恢复成功率提高。该 adapter 尚未接入机械臂反思服务；当前只训练文字反思，视觉与运动模块保持各自原有流程。

下一步应先修正已知反馈/运动问题、固定实验口径、积累足量可追溯数据并建立独立测试集，再运行正式微调与任务级对比。四卡释放后可加入 DDP 提高吞吐，不能直接把本单卡脚本的 GPU 数改为四。
