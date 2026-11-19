# 代码与文档

本次发布范围已按作者最新要求收窄为代码与文档。原始实验数据、图像、轨迹、NPZ状态、训练产物、模型权重和大型附件不在本次发布范围；此前建立的大文件Release草稿已撤回。

## 阅读入口

- [当前进度](CURRENT_PROGRESS.md)：批量任务提前停止的真实结果与限制。
- [本批结果摘要](GRASP_BATCH_20261119.md)：200项去向、4次实际尝试及工程错误。
- [research_workspace](../research_workspace/)：本地各版本源码、脚本、计划、报告和说明文档。
- [server_source](../server_source/)：服务器源码、配置、环境脚本、Slurm入口、场景XML和第三方许可证。
- [发布范围](../publication/20261119/CODE_DOCS_SCOPE.md)。

核心入口：[完整抓放运行器](../server_source/qualified_execution_v1/runtime.py)、[原始抓取流程](../server_source/improvement_20261019/code/grasp_process.py)、[单次入口](../research_workspace/qualified_full_task_trial_v1/worker.py)、[批量入口](../research_workspace/qualified_grasp_batch_v1/worker.py)。

## 使用说明

服务器原工作根目录为/home/yeliheng/grasp_server。历史环境脚本引用该路径；代码上传不代表已完成便携安装或新机器上的端到端复现。模型权重和原始数据仍在原实验环境。

历史报告中指向实验图像、JSON、日志或NPZ的链接可能依赖原实验目录，这些资料按最新要求不随本次上传。当前进度页提供自包含的结果摘要。不要重提已消费的作业、删除claim或覆盖历史失败。

第三方源码保留原有LICENSE、COPYING、NOTICE等声明，本次上传不改变许可证。既有仓库中此前发布的图表和精选证据保持；本轮新增范围只包含代码、配置与文档。
