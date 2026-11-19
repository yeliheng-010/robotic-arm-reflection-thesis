# 轻遮挡相机接线与首轮物理验证

目标：将camera_visibility_v6用于实际采集入口，并拦截运动后不合格观测。保持baseline/varied_noisy两场景，不覆盖旧源码、数据或模型。

架构：新目录包装冻结的StrategySession和Sampler；新配置只改camera，重新运行原几何资格；私有可见性统计不进入模型输入。原图不合格时中止公开观测，审计所需的图像单独存入private_audit。只使用已验证的5个相机选择产物，不重复相机搜索。

固定布局：964008、964009、964012、964294、964306，全部为已有train布局，任务RedBlock→BlueBin。最多5次新的首轮执行，每布局1次；历史首轮只读复用，不做恢复分支、不调用语言模型、不训练、不作为独立开发/最终测试。之前9布局的4个相机拒绝保留在资格分母。

风险：相机合格不保证噪声点云或规划合格；成功放入容器后可能自然遮挡，不能因此抹去物理成功，但应阻断后续公开输入。新旧视角造成噪声投影变化属于相机变化的下游影响。5个训练布局不足以推断泛化或语义识别收益。

步骤（执行中仅一项）：
- [x] 核对现有入口、Slurm队列和旧训练状态（6198完成31步/124条）。
- [x] 编写并运行接线回归测试，验证拒绝无回退、非相机不变、先检查后采集、缺失结果不能算失败。
- [x] 实现cc_prepare/cc_qualify/cc_runtime/cc_worker，冻结并验证新入口。
- [x] Slurm逐项执行5布局资格，合格才启动一次物理执行；保留拒绝和异常，不自动重跑。
- [x] 独立审计，核验历史与新结果身份、可见性、接触/运动/传感保护；汇总并更新检查点。

文件：cc_policy.py负责纯接线门槛；cc_common.py负责路径与身份；cc_prepare.py固定源与配置；cc_qualify.py复用原资格；cc_runtime.py负责初态与暂停观测检查；cc_worker.py执行一次并保留私有审计；cc_audit.py独立核对；cc_run.py调度与汇总。测试test_policy.py先失败再通过，Slurm使用env_sim/bin/python -B -m unittest discover -v。

验收：新配置只改相机；不合格观测不能调用公开采集；每布局最多1次执行；资格/执行/审计分母分别报告；必须有真实日志才能声明运行通过。使用短writing-plans、executing-plans、test-driven-development、verification-before-completion及requesting-code-review清单自审；用户允许的子代理型号不可用，不冒充独立代理审查。

完成证据：6397冒烟、6398五布局物理与独立审计均COMPLETED/0:0；旧1/5、新2/5；4个终态公开输入被阻断。详情见[REPORT.md](REPORT.md)。
