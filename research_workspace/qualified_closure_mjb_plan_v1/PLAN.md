# 固定MJB有限隔离闭合诊断 Implementation Plan

> 执行代理：使用 executing-plans 串行实施；本轮交付方案及零积分准备核验，后续实施步骤使用下列检查表。保留所有旧实验、失败和claim，不创建worktree、不使用Git。

**Goal:** 从已验证的唯一合成初态出发，检查原固定闭合控制的单次离散轨迹是否触发禁碰，并保存可独立复核的双时点证据。

**Architecture:** 新入口直接读取6878固定MJB和6875候选，使用6881的重载模型626字段作为精确身份基线。复用原碰撞分类、双时点采集和控制序列，独立实现零初始化预算、模型直接加载及轨迹审计入口。不得调用旧会创建环境并积分500步的执行器。

**Tech Stack:** Python 3.11、MuJoCo 3.3.7、NumPy、Slurm；GPU1/CPU2/16G/10分钟/no-requeue，与已验证来源环境一致。

方案日期：2026-11-18。当前用户采纳“制定有限隔离闭合诊断”的建议；本轮`execution_authorized=false`、`entrypoint_ready=false`。本目录prepare.sbatch仅验证方案及已有证据，不是动力学入口。新动力学预算必须与完成验证的执行代码一起另行登记；不继承旧v4已消费预算。

## 固定输入与目标边界

- 唯一模型：`qualified_scene_candidate_v1/run/model.mjb`，97,903,167字节，SHA256=7588512f3d6f11b9730423721e04e5106b418ef9d4a34749687de35268f1aaa0。
- 唯一候选：`qualified_initial_projection_run_v2/run/candidate_state.npz`的integration，SHA256=f36b22f5fef62ce9d66feb0c9de61a0905a890e5c669a4744bdc60a55c808596，1086项。
- 身份基线：`qualified_scene_static_audit_v2/run/model_fields.json`，626项，包括signature=0；以后每次重载和轨迹前后均要求与这份基线**全部精确相等**。625字段与原编译模型相等的来源证明由6881承接，不再临时删除字段。
- 布局978505，动作center/15mm/30°/135°/180°，源物体PurpleCapsule；六关节命令取原closure.command，与`qualified_closure_reachability_v1/run/input.json`一致，不取预抓取selected.q1。
- 模型时间步0.002秒、integrator=3、solver=0，其他模型字段完全不改。最大1000步对应2秒模拟时间；循环墙钟120秒单列，不能通过增加预算掩盖采集开销。
- 不重求解、放置机械臂、清零状态、settle、改关节/执行器/摩擦/相机/求解器。候选已完成几何投影，实际恢复后的全部积分状态必须与候选精确一致；不能再调用旧initial.prepare。
- 无真实接近过程。结果只适用于这个经过6个被动角投影的合成起点，不是原失败轨迹的回放，也不证明实际接近末态可达性。

## 建议预算与生命周期

|项目|独立新诊断上限|
|---|---:|
|轨迹|1次；工程失败或初态拒绝也消费|
|模型重载|执行入口1次；独立审计另1次|
|场景初始化、等待、退出积分|0步|
|闭合积分|最多1000步，每条命令只对应1次mj_step|
|重试、重启、额外停留|0|
|模型生成、完整抓放、训练|各0|
|独立证据审计|1次，积分0|
|执行作业/循环墙钟|600秒/120秒|

登记与执行分开：最终代码先经纯替身测试和零积分直接入口核验，再绑定代码、协议、准备结果和上述输入，生成独立授权。提交次数也登记为1；没有消费claim不表示可以自动重提。实际入口在Slurm/GPU/来源/授权检查后，以独占创建的claim消费本次轨迹，再加载MJB。claim永不清除。任何失败保留部分证据，不自动换目录重试。

本轮只创建`preparation/claim.json`用于单次方案验证；它明确`kind=plan_verification`、`dynamics_budget_consumed=0`，不能被后续动力学入口识别为执行授权。

## 恢复及控制语义

1. 开始即禁止环境构造、reset、MjSpec编译、渲染、split step、嵌套闭合及规划/优化；只允许一次from_binary_path。不得构造UR5GraspEnv、调用opened/cv_select.scene或退出时调用会step的环境清理。
2. 读取唯一MJB，对照6881重载基线全部626字段；核验MuJoCo版本、布局、回调全None、原手指/执行器/等式参数及六关节伺服映射。任一不符在任务积分0步拒绝。
3. 创建独立MjData，按mjSTATE_INTEGRATION恢复候选，set/getState精确往返。仅初始化阶段允许对live做一次forward，之后再次要求完整积分状态不变。初态保存state_0000，检查原静态准入；不为通过检查修改任何值。
4. 验证candidate的ctrl是原六关节命令加夹爪0，qvel/qacc_warmstart/qfrc_applied/xfrc_applied保持其已验证值，不再次清零。若不符合已冻结候选的起点语义，0任务步拒绝，不能临时修补。
5. 原UR5GraspEnv.step在非可视化时只是`data.ctrl[:] = action; mujoco.mj_step(model, data)`。新后端以同样两句实现，但所有mj_step必须经过绑定live model/data的一次性permit；禁止frame skip、mj_step1/2、未经permit的step和步数超限。
6. 初始u=0；严格沿用原逐次累加`u=min(u+0.2,255.0)`的1000项序列，逐项与已归档controls.json精确匹配，不用linspace或乘法重写。首项0.2，末项199.9999999999972；机械臂ctrl保持原六项命令，不逐步改写qpos/qvel，不强制左右spring相等。
7. 逐步核验`data.time-initial_time == completed_steps*0.002`，沿用原1e-9秒数值核对容差，不把历史初始时间重置为0。

## 停止判定和证据顺序

初态及每次积分后检查原`qualified_closure_v1.geometry.collisions`：环境禁碰+self_geometry自碰撞规则、源物体接触例外保持。分别对原积分后缓存和同一积分状态副本forward后的缓存分类，任一时点禁碰即禁止下一步。只允许forward副本，不为统一结果刷新运行轨迹缓存。

其他停止原因：非有限状态、MuJoCo警告、模型字段改变、初态准入失败、计数/时钟异常、日志失败、墙钟120秒或1000步预算耗尽。所有同时可观察原因记录；失败后不追加积分。每步检测不等于连续碰撞检测。初态严格连接阈值不能擅自挪作动态软约束“每步必须精确成立”的新规则；动态约束残差完整记录，沿用原停止规则。

顺序固定为：写入并fsync步号/控制意图 → 标记uncertain_step → 发放一次permit并积分 → 记录已返回步数 → 复制原缓存 → 在副本forward → 保存状态NPZ及分类JSON → 判停。记录native_step_requests、native_step_returns、completed_steps和uncertain_step；积分调用抛错时可能已部分推进，绝不记作确定0步。超时/进程中断时根据未匹配intent报告不确定尾步，不重启补采。

复用capture.pack的全部数组、接触geom/distance/position/frame、warning，以及完整积分状态。保存八个手指角/速度、spring差、执行器/被动力、机械臂漂移与TCP漂移。TCP使用2f85_base坐标加其旋转乘原tool平移[0,0,0.13]；方向不是新控制目标。对原5个碰撞构型保存八维角差最大绝对值及逐步最小值，不设事后“命中”阈值。

输出均独占创建，原始缓存和副本缓存分别命名。记录冻结来源、实际导入来源、模型MJB路径/大小/hash、626字段、初态、dt/积分器/求解器、每步意图/状态/结果与最终清单。不必再生成98MB相同MJB副本；必须证明原文件前后hash一致、持续保留供审计读取。

## 独立审计与结果解释

另一个Slurm进程只读同一MJB一次，禁止所有积分和环境工厂。使用执行阶段保存的重载626字段严格比较，不与6878非序列化编译签名混用。检查完整意图—完成记录序列、原ctrl序列、setup=0及无停止后积分；按原保存缓存重新分类，再从每个完整状态forward副本，与对应rebuilt时点逐字段精确比较，不要求跨时点相等。出现差异，保留审计失败，不能再按观察结果临时添加忽略项。

初态拒绝、禁碰停止、1000步未检出禁碰、超时、工程失败分别报告。任意有限轨迹都不解除原rejected/gripper_closure，不证明5个构型全局不可达，不提升生产ready或训练资格。保存证据不完整只能形成失败证据复核，不能称完整轨迹审计通过。

## 视觉协议保持

本候选姿态固定相机观察拒绝已经核验，拒绝图像不得提供项目模型或训练。原冻结动作已在历史合格输入上选定；本次只是私有物理诊断，不重新向模型请求动作或视觉。沿用闭合期间不重新观察的原协议。全14/85%/尺寸/连通性/6mm、3mm噪声/2%缺失均不改；不搜索相机，不将诊断轨迹冒充合格采集样本。

## 本轮方案核验

- [ ] 固定并逐份校验协议、候选、6881结果和模型字段、旧控制序列/命令/实现源码及旧失败claim。
- [ ] 在Slurm运行prepare.sbatch一次：只读已有JSON/NPZ/hash，不加载模型/数据、不重算静态几何、不重复旧测试；构造/积分/forward/渲染/闭合/规划/优化计数必须全0。
- [ ] 记录建议预算的类型/数值、动作/命令绑定、全部626重载字段、固定dt、控制序列精确一致，以及零动力学授权/入口状态。
- [ ] 归档准备结果、来源、日志及哈希，完成串行自审，更新REPORT和CURRENT_STATUS。

## 后续实现任务（本轮不建立动力学入口）

后续使用独立`qualified_closure_mjb_v1/`，不得修改旧目录。函数≤50行、文件≤300行；共享生产协议、根配置及依赖保持。

1. **protocol.py / test_protocol.py**：新ID、setup_steps=0和独立授权/claim验证，绑定最终源码及本方案。先用替身验证旧授权/旧ID、缺授权、变哈希、预算增加、第二次claim均拒绝。日志写入使用原save的独占+flush+fsync；未通过验证不能构造仿真。
2. **limits.py / test_limits.py**：只存在blocked/task两个阶段，没有setup分支。permit仅绑定一次live model/data，记录requests与returns；对wrong-model、wrong-data、nstep≠1、split step、超限、无permit逐项验证拒绝，原生抛错时requests保留、returns不加。
3. **restore.py / backend.py**：直接读取固定模型和候选；复用6881门禁证明，实际比较改为其626项重载基线精确相等。执行上述原参数/状态/初态检查；复用capture.observe和reference_vectors，替换仅依赖env.robot的TCP读取为冻结tool平移。不能复用旧entry.run_environment、initial.prepare或旧setup预算。
4. **worker.py / test_worker.py**：固定控制和每步停止，保留uncertain_step。替身用确定的第k步cached/rebuilt碰撞、警告、NaN、模型变化、时钟异常和写失败触发，逐项断言无k+1；0步拒绝及1000步耗尽也覆盖。旧28项测试不整套重复运行，只验证新入口差异与复用边界。
5. **audit.py / test_audit.py**：改为setup=0和新重载基线，复用原capture缓存分类及状态复算逻辑。对缺失/额外状态、未确认intent、错误控制、停止后多步、错误模型hash及状态重建差异必须拒绝。原完整审计仅接受无uncertain_step且证据齐备；其余输出失败证据。
6. **preflight.py / verify_entry.sbatch / REVIEW.md**：同GPU资源，先纯替身回归，再零积分直接导入/加载候选检查，验证无reset/compile/渲染/隐藏step及来源完备；记录新必要测试，不重跑6875–6881。最终审查通过后才能生成准备清单及申请登记具体一次动力学预算。本方案本身不含execute.sbatch。

后续命令以新目录为边界：`$SIM_PY -B -m unittest qualified_closure_mjb_v1.test_protocol qualified_closure_mjb_v1.test_limits qualified_closure_mjb_v1.test_worker qualified_closure_mjb_v1.test_audit`仅在Slurm执行。必须先看到这些新增门禁按预期拒绝，再完成实现并通过；真实动力学不用于调试入口。
