# 服务器只读检查：2026-10-19

> 以下为最初只读检查时的快照。随后已完成单卡7B QLoRA短训练（3608）、项目及资产迁移、EGL物理验收（3612），并启动冻结本地教师与60项采集。最新部署状态和Qwen3.5梯度失败/重试记录见 [服务器任务说明](../training/server/机械臂项目任务说明.md)；旧7B证据见 [验证记录](../training/qlora/VALIDATION.md)。共享base与GPU0/1服务未修改；尚未验证多卡训练。

通过原有 JupyterHub 登录完成。服务器报告时间：2026-10-18 16:16:59 UTC（北京时间 2026-10-19 00:16:59）。仅执行查询，创建的临时远程终端均已关闭；未安装依赖、下载权重或启动 GPU 任务。本记录不包含登录凭据。

## 当前资源

| 项目 | 检查结果 |
| --- | --- |
| GPU | 4 × Tesla V100-SXM2-16GB，总计 64GiB |
| GPU 0 | 已用 14661MiB，空闲 1484MiB |
| GPU 1 | 已用 15569MiB，空闲 576MiB |
| GPU 2 | 已用 0MiB，空闲 16145MiB |
| GPU 3 | 已用 0MiB，空闲 16145MiB |
| 已有 GPU 服务 | GPU 0/1 上为 `local-llm` 用户的 `strata` 进程，不修改该服务 |
| GPU 2/3 互联 | `NODE`，经过 PCIe/同 NUMA 域主桥；不是 NVLink |
| CPU | 80 个逻辑 CPU |
| 内存 | 总计 250GiB，available 144GiB |
| 用户家目录所在文件系统 | 剩余 300.5GiB；未检查用户配额 |
| 驱动 | 580.178.04 |
| CUDA 编译工具 | 12.9 |
| 操作系统 | el9_8 系列内核，glibc 2.34 |

`sinfo` 显示 `batch` 分区在线，单节点声明 `gpu:svc:2` 和 `gpu:v100:2`；`squeue` 查询未返回任务。后续应核对调度账号和 GPU 分配方式，通过适当的资源申请启动训练。显存空闲是检查时的快照，并不表示已为本项目预留。

## 软件与网络

- `conda env list` 仅列出 `/opt/anaconda3` 的 base 环境，base 本身不可写。
- 默认 Python 与该 base Python 均为 3.14.6。
- 两者未查到 PyTorch、Transformers、PEFT、Accelerate、bitsandbytes、vLLM、TRL。当前 Python 未查到 MuJoCo。
- 未查到 `jupyter-server-proxy` 的 Python 包元数据；尚未验证本机如何访问未来的模型服务端口。
- ModelScope、hf-mirror、PyPI 的 HTTPS HEAD 查询均返回 200；Hugging Face 直连在 8 秒内超时。这只证明站点可达，尚未验证具体权重仓库下载。

## 对部署与微调的判断

1. 适合先部署 3B 文本反思模型并进行小规模训练验证，再评估 7B 的 QLoRA；实际显存需加载与训练实测。
2. 在用户目录建立独立 Python 3.10/3.11 环境；不要在共享 base 中安装依赖。
3. V100 选择支持其 Volta 架构的 PyTorch/CUDA 与量化库组合，使用 FP16 计算，避免依赖 BF16、FP8 和不支持 V100 的注意力内核。服务器安装的 CUDA 12.9 不代表必须安装对应版本的 PyTorch wheel。
4. 两张 16GiB 卡不会自动合并显存；双卡训练需选择并验证具体并行策略。首先验证单卡小模型有助于缩小兼容性问题范围。
5. 初期保留本机仿真与视觉模块，在服务器提供反思推理服务；纯文本反思需要调整当前附带图像的调用路径。
6. 本次没有验证任何具体模型/训练框架组合能正常运行，也没有开始正式部署或微调。

训练数据准备与系统遗留问题见 [HANDOVER.md](HANDOVER.md)。
