# 固定MJB闭合入口：实现、30项测试与零步独立审计

已按[6882核验方案](../qualified_closure_mjb_plan_v1/PLAN.md)实现独立MJB入口、一次性步进控制、双时点采集及审计。30项新增测试通过，真实入口--verify恢复固定候选并保存零步证据，独立进程精确复核通过。本轮无初始化或闭合积分；**程序的执行前验证通过，动态闭合安全仍未验证**。

使用executing-plans、test-driven-development、串行代码自审和verification-before-completion；review依据requesting-code-review门禁执行，未声称独立子代理评审。指定子代理型号不可用，未委派。没有Git操作、环境/依赖更改、相机搜索、模型生成、完整抓放或训练。

## 实现边界

- `protocol.py`、`entry.py`：新诊断ID、初始化0/最多1000闭合步预算；授权必须绑定最终准备hash、完整来源、预算及审批引用，缺授权在仿真导入之前拒绝。轨迹claim独占创建，不复用旧v4授权。--verify和审计使用各自独立claim，不消耗动力学预算。
- `resources.py`、`restore.py`：只加载固定MJB，全部626项字段与6881重载基线精确相等；恢复唯一1086项候选，不再次放置、清零、求解或settle。原参数/伺服映射/状态/回调/初态检查保持；禁止环境构造/reset、编译、渲染、规划、优化和嵌套闭合。
- `limits.py`、`worker.py`：没有setup阶段；每条原控制命令只对应一次绑定live model/data的permit。原生调用前记requests、返回后记returns，证据落盘完成另记observed_steps。原生异常保留uncertain_step；意图或状态写入失败后不继续下一步。每步检查两时点禁碰、数值/警告、模型变化及时间一致性，循环上限120秒。
- `backend.py`、`pipeline.py`：零步验证与实际执行共用恢复/采集路径，只有执行模式能启用task阶段；初始live forward仅一次，后续forward只作用于副本。保留原碰撞分类与capture语义，记录8指关节角/速度、spring差、参考构型角距离、机械臂/TCP漂移及原缓存/重建缓存。
- `trace.py`、`audit_states.py`、`audit.py`：检查setup=0、精确文件集合、控制/步号/返回/停止顺序，分别重分类保存缓存和重建同一状态，逐数组精确比较；不要求跨时点相等。
- `partial.py`：中断/损坏证据只作failure_evidence_only字节保全复核，不认证原生完成步数或动力学通过；readiness明确拒绝此范围。完整轨迹缺记录、额外步、错误控制或不确定尾步均不能通过完整审计。

源码自审见[REVIEW.md](REVIEW.md)，实施范围见[IMPLEMENTATION.md](IMPLEMENTATION.md)。只复用旧commands/capture/碰撞策略等已冻结函数；不调用旧500步环境入口和initial.prepare，不修改旧代码或失败。

## 测试及源码绑定

6883首先执行22项新测试，22项均因缺实现发生预期断言失败，errors=0；真实模型/数据/编译构造和积分请求0。6884初版28项通过。自审补充“不完整证据不能取得ready”和测试源码绑定：6885仅执行相关3项，新增2项因缺partial模块预期失败，1项既有缺记录检查通过；两次红灯及修改前源码保留。

6886最终30项全部通过，errors=0，真实构造/积分请求仍0。覆盖旧/缺授权、增预算、变来源、重复claim、无permit、wrong model/data、frame skip、超限、split step、原生异常请求/返回分离、初态拒绝、两时点第k步停止、非有限/警告/模型变化、时钟异常、写失败、1000项原控制值、缺失/额外证据、停止后积分、重建数组错误和损坏JSON保全。

最终测试保存22份新Python源码执行前/后的SHA256并要求一致；preflight逐份核对最终源码，避免使用旧版本的通过结果。测试证据见[最终测试结果](evidence/remote/tests_6886.json)，[初始红灯](evidence/remote/tests_6883.json)、[补充红灯](evidence/remote/tests_6885.json)及[开发历史](evidence/remote/development)均保留。旧实验和旧测试套件未重跑。

## 实际GPU与零步证据

6887在原Tesla V100-SXM2-16GB、Open3D CUDA配置下登记8600项来源，真实导入过程中构造和积分请求全0；确认最终测试与当前源码一致。

6888调用新入口--verify：固定MJB加载1次，MjData创建2个（live和副本），live forward1、copy forward1。626项重载字段精确一致；1086项积分状态在恢复/初始forward后不变，ctrl及原零值字段检查通过，初态静态检查通过。只保存state_0000、observed_0000及恢复/模型元数据，没有控制意图或任务步；completed_steps=observed_steps=0、uncertain_step=null、reasons=[verification_only]。

6889是独立Slurm进程：固定MJB加载1次、数据副本1个、copy forward1、live forward0，全部对应重建数组、缓存分类及诊断量精确一致；task_steps=0，scope=full_trace且verification_only=true。**这里的完整审计仅指这份零步证据完整，不是1000步动力学轨迹通过。** 5个参考构型距离只来自初态，不能解释为闭合轨迹最小距离或可达性结论。

6888/6889的初始化、积分请求/返回、环境reset、编译、渲染、规划、优化、嵌套闭合和禁止入口计数全部0。真实非零停止分支仍只由替身测试覆盖，未做动力学实证。

证据见[入口结果](evidence/remote/verification/result.json)、[初态检查](evidence/remote/verification/initial.json)、[模型元数据](evidence/remote/verification/metadata.json)和[独立审计结果](evidence/remote/verification/audit_result.json)。

## 作业与归档

|作业|内容|状态/退出码|用时|
|---|---|---|---|
|6883|缺实现的22项红灯测试|FAILED / 1:0|1秒|
|6884|初版28项测试|COMPLETED / 0:0|4秒|
|6885|补充失败证据测试，3项中2项预期失败|FAILED / 1:0|1秒|
|6886|最终30项测试及源码hash绑定|COMPLETED / 0:0|5秒|
|6887|零构造导入准备、8600项来源|COMPLETED / 0:0|33秒|
|6888|同一入口的零步实际验证|COMPLETED / 0:0|89秒|
|6889|独立零积分状态/缓存审计|COMPLETED / 0:0|62秒|
|6890|准备条件与来源收尾核验|COMPLETED / 0:0|26秒|

收尾作业状态另见[Slurm记录](evidence/SLURM_STATUS.txt)，机器准备结论见[readiness.json](evidence/remote/readiness.json)。准备文件只标记entrypoint_ready=true、execution_authorized=false、dynamics_budget_consumed=0。无authorization.json、execute.sbatch、run目录或真实轨迹claim。

本轮66份远端文件、修改前源码、测试红/绿结果、准备清单、零步NPZ/JSON和日志集中在[下载清单](evidence/DELIVERY.json)，逐份SHA256核验及本地源码/报告链接检查见[最终核验](evidence/FINAL_VERIFICATION.json)。98MB MJB保留原服务器路径，本轮未下载或生成副本；固定SHA256仍为7588512f3d6f11b9730423721e04e5106b418ef9d4a34749687de35268f1aaa0。候选SHA256仍为f36b22f5fef62ce9d66feb0c9de61a0905a890e5c669a4744bdc60a55c808596。

## 当前阶段和下一步

现在处于“独立闭合入口及审计已实现，执行前测试和零步验证已通过，真实动力学预算待登记”的阶段。固定相机观察仍拒绝，不合格图像不进入项目模型或训练；原生产动作rejected/gripper_closure保持。

下一步可绑定最终readiness和完整来源，登记并执行一次隔离诊断：初始化0步、闭合最多1000步（最多2秒模拟时间）、循环墙钟120秒，任一时点禁碰或异常即停，失败不重试，随后一次零积分证据审计。此具体动力学预算尚未登记或消费；即使单条离散轨迹未检出禁碰，也不自动解除生产门禁或建立训练准入。
