# 固定MJB闭合入口实现与执行前验证

执行来源：../qualified_closure_mjb_plan_v1/PLAN.md，6882已核验。当前用户采纳实现入口、替身测试及零积分检查的建议；真实闭合预算不在本轮登记。

采用executing-plans、TDD、串行代码自审、verification-before-completion。指定子代理型号不可用，保持串行；不使用Git，不修改已冻结目录。

进度由REPORT.md记录，源码冻结后本文件不追写状态。

1. 新增纯替身授权、步数、停止、轨迹序列测试，Slurm确认缺实现时明确断言失败。
2. 实现protocol/limits/worker/trace，复用旧commands、碰撞规则与capture的物理语义；不复用旧500步环境入口或initial.prepare。
3. 实现直接MJB恢复、626字段完整身份检查、双时点采集、完整证据审计和导入/资源保护。
4. 替身测试通过后冻结最终源码和来源，登记零积分准备清单；执行同一入口的--verify模式，验证实际模型恢复及state_0000证据。
5. 独立审计只检查新入口产生的零步证据，不重放动力学、不重复旧实验。失败保留，不自动重试一次性入口。
6. 归档日志、测试前后源码、来源、状态和JSON/NPZ，更新当前状态。没有authorization.json、execute.sbatch或真实轨迹claim。

关键验证：缺授权在仿真导入前拒绝；setup不存在；原生requests/returns分开；wrong model/data、额外步及split step拒绝；失败保存不确定尾步；原缓存/副本缓存分别审计；模型MJB与626重载字段精确绑定；恢复前后1086状态不变；全部实际积分0。

零步入口和独立审计能验证真实恢复/采集/复算路径，但不能实证非零动力学、实际碰撞停止分支或完整抓放安全。后续真实预算仍需与最终入口及准备证据独立绑定。
