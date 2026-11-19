# 抓取与放置朝向分离

最新[完整物理验证报告](validation_v3/REPORT.md)：6468修订后单次胶囊任务成功，独立审计通过，原8开发条件累计已验证成功3/8。6461软件失败保留；同一条件累计两次真实尝试，不是两个独立样本。终态SortingTray未达到85%可见性，图像只私有审计，未新增训练数据。

156个安全放置端点、完整静态路径、GPU零运动匹配及软件修订历史见[REPORT.md](REPORT.md)。

- 原端点/体积：根目录ot_*，数值修订ot_volume_v2.py。
- 放置倾斜：tilt/；完整持物路径当前版本：path_v2/。
- 冻结执行版本：physical/；独立接线修订：physical_fix_v1/oc_runtime.py。
- 本地文字证据：evidence/remote/，交付索引：LOCAL_DELIVERY.json。
- 源码校验：SOURCE_VERIFICATION.json，88份源码脚本一致。
- 新验证：validation_v3/，新增62文字文件、9源码脚本校验；成功物理记录在远端trial_gpu_v3。

不要重提physical/execute_v2.sbatch或validation_v3/execute.sbatch，不覆盖已消费trial_gpu_v2/v3。新入口仅适用于已配对的冻结输入受控验证，未推广为通用新场景采集器。
