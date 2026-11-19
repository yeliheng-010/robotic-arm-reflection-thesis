# 代码与研究资料

本次按作者要求，将研究代码、报告、证据和原始资料补充到同一项目。代码快照保持原目录结构；同名文件位于不同版本或历史证据目录时保留，不合并覆盖。

## 仓库内可浏览内容

- [research_workspace](../research_workspace/)：本地研究工作区的全部可发布源码、脚本、计划、报告、JSON/JSONL记录、图表、NPZ证据等；保留各版本和历史失败。
- [server_source](../server_source/)：服务器已有源码、说明、环境脚本、Slurm入口、机器人/场景XML及OBJ/STL资产，保持服务器相对路径。
- [当前状态](../research_workspace/CURRENT_STATUS.md)：最新结论在前，后续为历史截点。
- [完整批次证据](../research_workspace/qualified_grasp_batch_v1/evidence/remote/)：200项去向、4次真实尝试、停止堆栈、末态、遥测和作业记录。

核心执行入口包括[完整抓放运行器](../server_source/qualified_execution_v1/runtime.py)、[原始抓取流程](../server_source/improvement_20261019/code/grasp_process.py)、[单次包装器](../server_source/qualified_full_task_trial_v1/worker.py)和[批量入口](../server_source/qualified_grasp_batch_v1/worker.py)。服务器路径快照中的旧REPORT.md可能保留部署时状态，最新结果以本仓库当前进度和原始result.json为准。

## Release原始资料

[research-archive-20261119](https://github.com/yeliheng-010/robotic-arm-reflection-thesis/releases/tag/research-archive-20261119)提供原始研究资料分卷：

- `server-source.tar.gz`：服务器源码与场景资产完整包。
- `latest-batch.tar.gz`：本批完整原始记录。
- `research-data-001.tar.gz`起的分卷：已有实验图像、轨迹、JSON/JSONL、NPZ状态、训练数据和本项目训练产物等。每个分卷是独立tar.gz，可全部解压到同一空目录；不要直接拼接压缩包。
- `ARCHIVE_MANIFEST.json`：分卷名、大小、SHA256和文件计数。
- `EXCLUSIONS.json`：基础模型、虚拟环境、缓存、凭证文件等排除项。
- `REDACTIONS.json`：导出副本中被替换的凭证痕迹；原实验环境中的文件未改动。

仓库内清单见[publication清单](../publication/20261119/)。本地用于传输的base64包装和重复ZIP导出不再重复上传；解码后的研究证据和原图保持。

## 获取与使用边界

服务器原工作根目录为`/home/yeliheng/grasp_server`。环境脚本包含该实验环境的路径；克隆仓库不等于已安装MuJoCo、机器人依赖、GPU运行环境或模型权重。先阅读相关目录的环境脚本和历史报告，配置新环境并使用新的输出目录。

不应直接重提已经消费过的execute.sbatch、删除claim或覆盖失败记录。Release保留原始运行数据，供复现和分析，但本次没有重新运行历史实验或验证所有历史入口在新机器上的兼容性。

下载的Qwen基础模型不重新分发；依据相应模型目录、部署脚本和上游模型说明获取。代码快照中的第三方源码与机器人资产保留其LICENSE等原有声明；本次上传不改变其许可证。
