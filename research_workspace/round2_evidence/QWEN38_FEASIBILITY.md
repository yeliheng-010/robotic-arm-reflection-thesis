# Qwen3.8-Flash-Next 本机运行可行性

结论：原版 BF16 无法全部放入这台机器的四卡显存。量化 GGUF 加 CPU/GPU 混合卸载具有容量上的可行性，但本次尚未安装推理引擎、下载模型权重或执行该模型，不能称为已跑通。

## 已核实的机器条件

- 4 × Tesla V100-SXM2-16GB，共 64 GiB 显存；四卡 Slurm 分配与张量计算 smoke 作业 3900 已成功。
- 2 × Xeon Gold 6148，40 个物理核心、80 个逻辑线程，支持 AVX2/AVX512。
- 系统内存 268,484,530,176 bytes（约 250 GiB），检查时可用约 218 GiB。
- **Slurm 节点公布的可调度内存只有 120000 MiB，约 117.2 GiB**。不能直接把物理内存总量当作单个作业可用量。
- `/home` 检查时剩余 244,796,829,696 bytes，约 228 GiB；不足以直接下载约 335 GiB 的原版。
- 当前训练环境：PyTorch 2.6.0+cu124、Transformers 5.20.1、bitsandbytes 0.49.2、PEFT 0.21.2。配置映射识别 `qwen4_exp` 与 `qwen4_exp_text`；这只证明架构注册存在，不证明整模型运行成功。
- 该 Python 环境未安装 vLLM、SGLang、KTransformers；当前 shell PATH 中未发现 llama-cli/llama-server。系统编译工具为 CUDA 12.9.86、CMake 3.31.8、GCC 11.5.0，具备单独准备 llama.cpp 构建的基础条件，尚未进行实际构建。

## 官方原版权重

[用户指定仓库](https://huggingface.co/Qwen/Qwen3.8-Flash-Next)，核对 revision `de4b8e4d43b917e7706784d8bb445c9af86a3540`。

HF API 给出 179,999,981,424 个 BF16 参数及 35 个 I64 参数；索引 `total_size=359999963128` bytes，即 **335.28 GiB**。131 个 safetensors 文件含头部共 360,000,192,888 bytes。本地工作区的 `round2_evidence` 保留配置、索引和 API 元数据，未下载权重。

“6B 激活”描述每个 token 使用的计算规模，不代表只需要存储 6B 参数。即使假定全部参数理想地压到 4 bit，仅载荷也约 **83.82 GiB**，仍高于 64 GiB；实际量化还包含较高精度张量和量化元数据。CPU 卸载可改变显存需求，因此这一比较不等于所有混合部署方式都不可能。

## 可以考虑的量化路线

[llama.cpp 团队维护的 GGUF](https://huggingface.co/ggml-org/Qwen3.8-Flash-Next-GGUF)，核对 revision `91fb00353e766eb43944ed223665ea4fb87dad47`：

| 主模型文件 | 两分片合计 | 说明 |
|---|---:|---|
| IQ4_NL | 102,048,919,008 bytes，约 95.04 GiB | 优先试验候选，仍需 CPU 卸载 |
| Q2_K | 83,128,778,464 bytes，约 77.42 GiB | 更低精度，需额外检查质量损失 |

以上仅主模型；图像输入需要另加 mmproj，MTP 是可选侧模型。GGUF 使用混合精度，不能简单用文件名推算所有张量精度。该仓库还列有 DFlash 侧模型，不能将它混入本次基础模型比较。

[llama.cpp 构建文档](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md)仍描述 V100 的量化矩阵计算路径；这是选用它做兼容性试验的依据，尚不是指定模型在此 V100 上运行的证据。

建议的后续最小试验：独立目录与固定 llama.cpp revision；CUDA 构建面向 sm_70；下载固定版本的 IQ4_NL 主模型；通过 Slurm 申请资源；先单请求、2048–4096 上下文、不启用 MTP，将部分层/专家留在 CPU。记录模型加载峰值 RAM/VRAM、首 token 延迟、生成速度、短中文回答及反思 JSON 输出。须给 Slurm 内存限额和模型加载临时内存留余量，无法装入时调整卸载策略或停止，不绕过调度器。

## 其他引擎与结论边界

[vLLM 官方部署说明](https://recipes.vllm.ai/Qwen/Qwen3.8-Flash-Next)给出 BF16 335.28 GiB、FP8 172.78 GiB，并列出 H100/H200/GB300 的部署条件；这些配置不能直接照搬到 V100。

[SGLang 官方部署说明](https://docs.sglang.io/cookbook/autoregressive/Qwen/Qwen3.8-Flash-Next)的 NVFP4 路线面向 Blackwell；V100 缺少对应原生低精度计算能力，不能根据“4 bit”便认为兼容。

当前建议：继续用已验证的 Qwen3.5-4B 承担论文微调主线。Qwen3.8-Flash-Next 可作为独立量化推理/教师候选试验；是否达到可用吞吐、能否正确处理反思任务，都应以实测为准。现有 Qwen3.5 LoRA 不能直接加载到 Qwen3.8 上。
