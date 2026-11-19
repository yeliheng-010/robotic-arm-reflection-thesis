# 模型服务恢复后续跑

原因已核验：原资格筛查4922及门槛4923完成，但闭环冒烟4924在启动ready检查时发生ConnectionRefusedError(111)，尚未派发实验worker。原批量4926因依赖失败取消；原结束审计4927正常运行只说明已完成资格记录通过，complete=false、闭环accounted=0。

此次检查模型列表已恢复，独立generate探针实际回答OK，error/service_error均为空。没有重启或停止任何他人服务。

恢复只新增本目录调度器，复用冻结hardstudy.run.execute和原worker、任务列表、输出目录、资格结果；原失败stages/loop_smoke和原jobs.json保留。恢复阶段状态写本目录stages，恢复批量必须等待本目录新冒烟门槛。原实验protocol.json不变，恢复代码另由manifest.json冻结。

2项调度测试通过：运行新的阶段不覆盖旧失败记录，缺少新的冒烟门槛时批量被阻止。任务分母400、单任务最多3次尝试、策略、噪声与模型参数均不变，没有隐藏重试或重做资格筛查。

新作业：5020闭环冒烟→5022门槛→5023批量→5024结束审计。5020双分片已RUNNING，后继等待依赖。阶段冒烟20条复用到400总分母，不额外计样本。物理成功率不作为继续采集门槛；服务故障及审计不一致仍阻止后继。

资格当前200/200，189个challenge、11个easy_control，共400次控制/干预执行。第三批闭环尚未完成，新微调尚未启动。报告入口仍为父目录verification.json、REPORT.md；实时恢复进度以本目录stages下progress.json为准。
