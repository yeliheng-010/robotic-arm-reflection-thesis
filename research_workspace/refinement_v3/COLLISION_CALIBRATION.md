# 已验证的碰撞注入与下一阶段候选配置

旧位置高度扫描 12/12 完成（作业 4740）；紫色胶囊新路线扫描 6/6 完成（作业 4747）。两组都仅运行默认策略一次，不调用模型。失败和未触发条件全部保留。

|路线|障碍体位置 XYZ（米）|几何半尺寸 XYZ（米）|几何局部位置 Z|默认执行结果|
|---|---|---|---:|---|
|RedBlock → BlueBin|1.20, 0.355, 0.74|0.34, 0.012, 0.19|0.19|RedBlock 与 SafetyDivider 实际接触，collision|
|PurpleCapsule → RedBin|1.3575, 0.84, 0.74|0.0375, 0.012, 0.19|0.19|2f85_base 与 SafetyDivider 实际接触，transport 阶段 collision|

这些仅是后续独立实验的候选配置，未替换正在运行的 96 次原场景回归，也未验证反思恢复成功率。选择依据是默认执行触发目标碰撞，未看模型恢复结果。

紫色胶囊校准全结果：

|半高（米）|结果|阶段|接触对象|
|---|---|---|---|
|禁用|成功|完成|无|
|0.06|成功|完成|无|
|0.12|碰撞|descent|ur5e_base — SafetyDivider|
|0.15|碰撞|descent|ur5e_base — SafetyDivider|
|0.19|碰撞|transport|2f85_base — SafetyDivider|
|0.22|碰撞|pregrasp|2f85_base — SafetyDivider|

旧位置 Y=0.355 不在紫色胶囊 Y≈0.453—1.031 的搬运路线内。直接移动原宽障碍会干扰场景中的其他杂物：Y=0.72 与绿色圆柱位置重叠；Y=0.82 虽避开四个任务物体，仍被完整 qpos 初态核验拦截。相关中止记录保留在 collision_route_v1/v2。

最终使用窄障碍，检查完整 MuJoCo 场景中 57 个可接触体的保守边界；最小轴向间距约 12.2 mm。忽略不参与接触的视觉标记，允许与作为底面的 simple_table 接触；它的顶面 Z=0.74 已核对。每个真实校准运行随后再次验证所有初始 qpos 与无障碍控制一致（atol=1e-8），六次全部通过。

后续更换布局、物体、种子或噪声时需要重新核验初态和实际触发率；不能将这两个干净开发条件直接视为全部噪声条件都有效。0.12/0.15/0.22 的阶段不同，也不能都算作搬运碰撞。

服务器证据：`/home/yeliheng/grasp_server/refinement_v2/collision/result.json`、`/home/yeliheng/grasp_server/collision_route_v3/result.json`、`geometry_check.json`、`protocol.json`。
