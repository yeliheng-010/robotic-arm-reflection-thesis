# 6881序列化身份与静态独立复算通过

6881 COMPLETED/0:0，60秒。七项审计门禁测试通过，核验8544项冻结来源；读取原MJB一次、恢复唯一候选、forward一次。reset、compile、渲染、积分、闭合、规划和优化全部0。625个序列化字段精确匹配，只允许预先绑定的signature从10107167426275082415变为0；原6879的626项完全相等审计仍失败，未改写签名或旧文件。

原connect、driver、attach、14项有限关节限位、环境/自碰撞规则、有限值和警告检查独立复算通过，与6878 static.json按原报告比较atol=1e-12一致；物理门槛保持。48条总接触中禁碰0，1086项积分状态及全部重载模型字段不变。见[本次结果](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_static_audit_v2/run/result.json)、[静态检查](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_static_audit_v2/run/static.json)。

签名差异依据[官方3.3.7 engine_io.c](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/src/engine/engine_io.c)、[mjxmacro.h](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/include/mujoco/mjxmacro.h)、[mjmodel.h](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/include/mujoco/mjmodel.h)和[user_model.cc](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/src/user/user_model.cc)。原文件已归档在[reference](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_static_audit_v2/reference)，安装的两个头文件哈希与官方文本一致。独立signature未包含在MJB写入/读取宏中；加载分配模型时清零，编译路径才设置该签名。pair_signature及exclude_signature未被排除。

不重新采集观察；沿用6880已核验的观察拒绝结果。通过本审计不表示综合资格或动态闭合安全通过。完整事实、限制和下一步见[综合报告](../qualified_scene_candidate_v1/REPORT.md)；[最终归档核验](../qualified_scene_model_diagnostic_v1/evidence/FINAL_VERIFICATION.json)记录本地文件与远端原件的哈希一致性。
