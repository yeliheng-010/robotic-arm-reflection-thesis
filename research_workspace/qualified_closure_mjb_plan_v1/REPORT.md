# 固定MJB闭合诊断方案与零积分准备核验完成

已把下一步限定为：从已验证的固定模型和候选出发，运行一次最多1000步的隔离闭合诊断，初始化预算0，禁碰即停、失败不重试。本轮完成方案、机器协议、源码语义核对及Slurm只读准备验证，**尚未实现动力学入口、登记新执行预算或推进闭合**。

执行依据是用户采纳“制定有限隔离闭合诊断”的建议。使用writing-plans、verification-before-completion和串行自审；未做Git、环境安装、相机搜索、模型生成或训练。

## 与旧方案相比的必要变化

- 直接读取6878的MJB，恢复6875唯一候选的1086项完整积分状态；不调用旧opened/reset及initial.prepare，不再执行500步初始化、放置变换或清零状态。
- 后续模型身份以6881保存的重载模型626项字段为精确基线，包括signature=0。原编译签名差异已有证据解释，后续执行/审计无需放宽字段比较；旧6879失败保留。
- 原机械臂命令、1000项夹爪逐次累加序列、模型参数和禁碰规则保持；0.002秒时间步对应最多2秒模拟时间，墙钟120秒另计。
- 新入口必须分别记录native_step_requests、native_step_returns和uncertain_step，避免原生调用异常时把不确定尾步记为0；双时点原缓存/副本forward任一触发禁碰均禁止下一步。
- 旧执行器硬编码setup=500，旧审计也检查setup=500并比较编译指纹，因此不能直接复用旧入口；可以复用原控制序列、碰撞分类、capture.observe和参考构型距离定义。

完整操作边界、预算、落盘顺序、停止条件、结果解释与六项后续实现任务见[PLAN.md](PLAN.md)，机器字段见[protocol.proposed.json](protocol.proposed.json)，源码核对见[SOURCE_REVIEW.md](SOURCE_REVIEW.md)。方案固定后没有修改或重跑旧实验。

## 6882实际核验

作业6882为COMPLETED/0:0，60秒；队列为空。它在模型/数据/编译/积分阻断器内核验8554项继承及新增来源，21项直接输入/源码绑定；所有计数为0：integration、model_construction、data_construction、spec_construction、forward、rendering、reset、environment_step、close、planning、optimizer。

核验内容包括：模型97,903,167字节及SHA256一致、候选hash一致、6881静态审计通过且状态未变、重载基线626项及signature=0、仅原编译signature一项不同、dt/积分器/求解器一致、六关节命令/动作绑定、1000项控制序列逐元素相等、5个参考碰撞构型、实际导入的step/close源码与旧快照逐字节匹配、原tool平移0.13m、旧v4 claim=1及失败不变。

首项夹爪控制0.2，末项199.9999999999972；建议预算为轨迹1次、初始化0步、闭合最多1000步、零积分审计1次、模型/完整任务/训练各0。这里核验的是已有控制列表与方案的一致性，没有运行控制、重新计算静态几何或重复之前的测试套件。

唯一新claim位于preparation/claim.json，kind=plan_verification、dynamics_budget_consumed=0；协议及结果均明确execution_authorized=false、entrypoint_ready=false。无authorization.json、execute.sbatch或run目录，尚无新动力学实现目录。详见[准备结果](evidence/remote/preparation/result.json)、[准备claim](evidence/remote/preparation/claim.json)和[作业状态](evidence/SLURM_STATUS.txt)。

## 验收与证据

- [x] 固定模型、候选、基线、动作、原命令和源码，绑定hash。
- [x] 明确初始化0、有限闭合、每步停止、请求/返回/不确定尾步及失败保留规则。
- [x] Slurm零构造/零积分准备核验通过，未重复几何实验。
- [x] 12份远端文件逐份SHA256归档，7份本地冻结方案/源码与远端一致；本地仅做归档及语法/长度核验。
- [x] 后续实现、测试、审计和登记边界具体化，当前状态同步。

见[下载清单](evidence/DELIVERY.json)、[最终核验](evidence/FINAL_VERIFICATION.json)。98MB模型仍在原服务器路径，本轮只核验hash/大小，不新增模型下载；上轮完整证据在[场景报告](../qualified_scene_candidate_v1/REPORT.md)。

当前处于“静态初态已验证、零初始化闭合方案已核验、动力学入口待实现”的阶段。固定相机观察仍不合格，不合格图像不进入项目模型或训练；生产动作仍rejected/gripper_closure。方案核验不证明真实闭合安全或尚未实现的程序正确。

下一步按本方案实现独立MJB入口和审计，先以替身测试验证预算/停止/失败路径，再做零积分直接入口检查；通过后才将具体执行代码和一次性预算一起登记。真实闭合不用于调试入口，也不自动继承旧v4授权。
