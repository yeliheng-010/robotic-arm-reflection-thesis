# 有界抓取与观测覆盖修订

最新结果见[REPORT.md](REPORT.md)：剩余胶囊1024新端点均拒绝；两个初态新增60/54视角均拒绝；保存终态相机方位+5°后全14物件合格，独立复算通过。物理任务成功仍3/8，新增物理/模型/训练均0。

当前候选实现proposals.py；相机登记修订camera_registration.py / camera_runner_v2.py。旧common.py、manifest.json保留原baseline选择错误，仅作历史记录；不要重提run.sbatch。camera_v2.sbatch也已消费，不应重复覆盖已存probe/audit。

终态重渲染尚未接入实时任务，也未发布训练数据。最终冻结清单用final_review.json；运行中review.json仅作历史快照。所有结果、源码哈希与图像在本地evidence/remote、examples和交付清单中可查。
