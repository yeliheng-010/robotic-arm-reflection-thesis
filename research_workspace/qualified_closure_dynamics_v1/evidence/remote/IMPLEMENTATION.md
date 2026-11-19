# 受控闭合诊断：实现与验证范围

本目录承接 ../qualified_closure_dynamics_plan_v1/PLAN.md。当前用户授权为实现与定向验证；没有真实动力学预算，没有 authorization.json，没有 run/claim.json，没有真实运行 sbatch。test.sbatch / verify.sbatch 仅运行测试及准备来源清单。

## 入口与边界

- protocol.py：只读取外部独立授权并核验，不能自动授权；一次claim在初始化前独占写入，失败不删除。授权必须包含明确用户批准记录、固定诊断ID、精确整数预算、准备清单哈希及完整来源集合。
- entry.py：必须在Slurm且具有独立授权；授权缺失时在bootstrap/仿真导入前拒绝。复用旧环境初始化/快照恢复，禁止生产闭合函数，绝不调用完整抓放入口。
- limits.py：最多500初始化调用，每次任务积分必须取得绑定model/data的单次permit，最多1000；分步积分、frame skip、隐藏额外步和退出积分均拒绝。
- initial.py：固定closure.command，保留初态手指/物体，清零速度/热启动/外力，原伺服保持；不做IK、重试或额外settle。
- capture.py / backend.py：原缓存与独立forward分开保存，检查采集前后积分状态及缓存不变，逐步保存接触/速度/力/漂移/约束/警告、五构型距离。来源模型指纹在每次观察检查，文件来源运行前后检查。
- worker.py：纯后端循环，初态及每步任一时点禁碰即停；失败步意图保留，不把可能部分执行的步记为确定未执行。证据写入失败立即停止后续积分。
- audit.py：仅加载MJB/证据，不创建场景、禁止积分；核查控制、停止位置、轨迹计数和双时点各自一致性。非完整轨迹或工程失败不得获得完整审计通过。

## 初态校验容差的落实

connect继续采用1e-7 m，driver等式采用1e-7 rad。attach是原生WELD，用MuJoCo的efc_pos各分量绝对值不超过1e-6校验合成起点；其旋转分量是MuJoCo残差表示，不能称为纯角度容差。该1e-6仅用于判定人工放置是否与原attach一致，不改生产禁碰阈值或模型约束参数。残差不满足即0任务步中止，不根据实验结果放宽。

初始化参数、MJB重载和真实场景的约束适配目前未由动力学实验证实。假环境测试及源码检查不等于实际运行通过；首次授权诊断也可能在0任务步初态检查中止，并消耗一次claim。

## 验证办法

预算/停止行为使用纯假后端，关键路径先见红再实现。测试覆盖缺授权、重复claim、来源变化、额外预算、初态拒绝、两时点分别触发、NaN/警告/模型变化、写入失败、步进异常、超时、原1000项命令、额外步及退出阶段阻断。capture测试以假对象替代forward，不进行MuJoCo积分。

verify.sbatch使用test_runner.py阻断真实mj_step/mj_step1/mj_step2与环境工厂，之后prepare.py仅检查语法、长度、控制和旧来源哈希，写execution_authorized=false的preparation_manifest.json。测试和准备必须均通过才算本次实现验证完成。

后续若明确授权一次动力学预算，先将最终准备清单绑定到授权文件，再在Slurm运行entry；不修改本目录已冻结源码，发现工程问题用新版本保存修复与失败记录。单次无碰撞不能解除旧rejected/gripper_closure或建立训练准入。

本轮按executing-plans、test-driven-development、requesting-code-review与verification-before-completion执行。受可用模型约束，采用串行代码自审，不宣称独立子代理review。
