# 6879原完全相等审计失败，记录保留

6879为FAILED/1:0、32秒。核验来源后加载6878保存MJB，在全部626项模型字段完全相等断言处失败；尚未恢复候选、复算静态检查或复核RGB。binary_load=1，其余积分/环境step/闭合/规划/优化/reset/compile计数0。未生成result.json，不重跑或改写本目录冻结审计。

后续6880定位唯一差异signature，625项其余字段精确相等，并独立复核保存RGB/资格拒绝。6881依据MuJoCo 3.3.7的MJB序列化语义，在独立新目录完成625字段精确身份和原静态检查复算。6879的原完全相等失败不改变。详见[综合报告](../qualified_scene_candidate_v1/REPORT.md)、[本次失败](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_candidate_audit_v1/run/failure.json)和[后续审计报告](../qualified_scene_static_audit_v2/REPORT.md)。
