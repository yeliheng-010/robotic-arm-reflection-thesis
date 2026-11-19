# 6880定位MJB编译签名差异，保存观察复核仍拒绝

6880 COMPLETED/0:0，60秒。仅重载一次6878保存MJB，未恢复候选或运行forward；积分、reset、compile、渲染、闭合、规划和优化均0。核验8530项冻结来源，5个延迟加载PyOpenGL文件与原已冻结安装RECORD匹配。

626字段中唯一差异为signature：10107167426275082415→0，其余625项精确相同。完整新指纹与差异见[model_difference.json](evidence/remote/qualified_scene_model_diagnostic_v1/run/model_difference.json)。后续官方MuJoCo 3.3.7源码核查确认该编译签名不由MJB序列化；两个安装头文件与官方版本完全一致，详见[新静态审计报告](../qualified_scene_static_audit_v2/REPORT.md)。诊断没有修改原6879审计或豁免其失败。

本次只解码旧RGB，复核原稳定性、initial/post和保存measurements对应的资格判定，仍拒绝SortingTray/PurpleCapsule/OrangeSphere/Hammer。没有重新渲染、重算分割/深度测量或标定；[保存像素PNG](evidence/remote/qualified_scene_model_diagnostic_v1/run/saved_observation.png)只是研究人员私有证据，不是项目模型/训练输入。

本目录集中归档四个阶段，共62份远端小文件；98MB MJB保留服务器，按size/hash列在remote_only，6880/6881核验。见[DELIVERY](evidence/DELIVERY.json)、[最终核验](evidence/FINAL_VERIFICATION.json)、[综合报告](../qualified_scene_candidate_v1/REPORT.md)。本地verify_archive.py只做字节、源码和记录核验，不执行数值实验。
