# 7B QLoRA：服务器短训练验证

模型为 `Qwen/Qwen2.5-7B-Instruct`，训练目标是根据机械臂失败证据输出反思 JSON。本入口处理文字证据；不训练视觉编码器、抓取网络或机械臂控制策略。

2026-10-19 已在单张 16GB V100 上完成 8 步训练、保存及重载验证；实际输入 326 token，PyTorch 峰值已分配 9.260GiB、预留 9.705GiB。详细记录与限制见 [VALIDATION.md](VALIDATION.md)。

## 环境与资源

服务器工作目录为 `~/grasp_qlora`。使用独立 Python 3.11 环境，PyTorch 2.5.1/cu121；其余依赖见 `requirements.txt`。V100 使用 FP16，不启用 BF16、FlashAttention 2。加载使用 NF4 4bit、double quantization，LoRA rank 8、alpha 16，覆盖注意力及 MLP 的七类线性投影；启用梯度检查点。

已核对 Slurm：`batch` 分区的 `gpu:v100` 对应物理 GPU 2/3；`gpu:svc` 对应现有服务使用的 GPU 0/1。脚本申请一张 `gpu:v100`，不修改 `CUDA_VISIBLE_DEVICES`。Slurm 会将分配到的设备映射为进程内的 `cuda:0`。

首次在新目录准备环境和权重：将本目录文件复制至服务器 `~/grasp_qlora/`，在该服务器终端运行：

```bash
cd ~/grasp_qlora
bash setup_server.sh
env/bin/python download_model.py --root "$PWD"
```

安装仅写入工作目录内的环境与缓存，不修改共享 base。权重约 15.24GB；下载器支持断点续传并保存文件校验清单。

## 数据

在本地项目根目录导出已验证的修正：

```bash
python -m training.qlora.export_verified \
  --input logs/reflection/experiments/pilot10_q122b \
  --output logs/reflection/qlora_dataset_new
```

输出目录必须不存在或为空。将生成的 `train.jsonl` 和 `dataset_manifest.json` 放到服务器 `~/grasp_qlora/data/`。导出器仅保留 LLM 给出修正、紧接着的下一次执行参数匹配且物理执行成功的记录，按内容去重。故障注入标签、未来成功结果和图片路径不进入模型输入；仅 assistant 回答参与损失计算。超过长度上限时明确报错，不截断答案。

当前 122B 十任务运行仅导出 **1 条**有效修正，因此只能用于验证训练流程。该样本含仿真监控提供的证据，不代表真实机械臂传感器具有相同信息。正式训练前需积累多物体、多指令、多故障及正常成功任务；按场景/任务族划分训练、验证、测试集，避免同一轨迹及近重复样本跨集合。

## 启动与检查

首次短训练在服务器终端运行：

```bash
cd ~/grasp_qlora
sbatch --parsable smoke.slurm
squeue -u "$USER"
tail -f smoke.log
```

训练为 8 个优化器更新步、微批次 1、梯度累积 2、最长 512 token。对单条样本的重复训练只检查代码和资源，不构成模型效果实验。

结果位于：

- `runs/smoke/smoke_result.json`：版本、数据哈希、损失、梯度、时间、显存与验证结果。
- `runs/smoke/training_progress.json`：当前阶段和最近一次更新。
- `runs/smoke/adapter/`：LoRA adapter、配置与 tokenizer；加载时仍需要原始 7B 基座。

输出目录非空时程序拒绝运行，保护已有结果。重试或比较不同长度时使用新目录，例如：

```bash
cd ~/grasp_qlora
srun --partition=batch --gres=gpu:v100:1 --ntasks=1 \
  --cpus-per-task=4 --mem=24G --time=00:15:00 \
  env OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 \
      TOKENIZERS_PARALLELISM=false HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  "$PWD/env/bin/python" "$PWD/smoke_train.py" \
  --model "$PWD/models/Qwen2.5-7B-Instruct" \
  --data "$PWD/data/train.jsonl" --output "$PWD/runs/smoke_retry_01" \
  --steps 8 --max-length 512 --gradient-accumulation 2 --rank 8
```

脚本检查有限损失、非零有限梯度、参数实际改变、adapter 保存重载后 logits 一致，并记录一次生成。生成是否为 JSON 仅为诊断信息；未测量独立测试集表现和机械臂任务成功率。当前不保存完整优化器状态，不支持训练中断后精确续训。

## 后续两卡、四卡

先用单卡实测确定序列长度及批次，再单独加入并验证 DDP。普通 DDP 每张卡保留完整量化基座，增加卡数主要提高吞吐；四张 16GB 不等同于一张 64GB 卡。更长上下文或更大模型需另行评估 FSDP/ZeRO 的量化兼容性和通信开销。

当前短训练入口明确只允许一张可见 GPU，不能直接将 `--gres` 改为四卡。未来释放 GPU 0/1 后，还需按服务器调度策略开放这些服务卡给训练；届时再实现两卡/四卡启动、正确数据分片和有效批次控制。现有服务不因本测试而停止。
