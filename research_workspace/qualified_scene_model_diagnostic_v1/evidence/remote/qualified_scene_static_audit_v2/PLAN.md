# 固定MJB序列化身份与静态复算

6879原626字段完全相等审计失败保持；6880只读诊断证实唯一差异为signature，从10107167426275082415变为0，其他625项完全一致。继续原已授权但未完成的候选静态独立复算，不重复场景实验。

MuJoCo官方3.3.7源码：mjmodel.h将signature定义为与编译mjSpec共享的编译签名；engine_io.c的mj_saveModel仅写MJMODEL_INTS、opt/vis/stat和MJMODEL_POINTERS，mjxmacro.h两个宏不含独立signature；mj_makeModel分配后清零，二进制加载路径没有重建该签名。user_model.cc在编译时赋值、CopyBack时检查签名。这不适用于忽略pair_signature或exclude_signature，它们必须精确匹配。reference保存官方原文件，两个头文件与服务器安装版本SHA256一致。

来源URL：https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/ 后接 src/engine/engine_io.c、include/mujoco/mjmodel.h、include/mujoco/mjxmacro.h、src/user/user_model.cc。这些参考文本只读，不编译或替换安装文件。

新独立审计明确报告序列化身份，而非修写旧626字段判定。字段集合/数目必须完全一致，唯一差异及原/新signature固定绑定；625个其他字段须精确相等，不改写内存signature或MJB。任何额外差异均拒绝。七项测试覆盖预期签名、参数变化、字段遗漏/增加/更名、签名异常。

单作业仅读取同一MJB一次、创建数据并恢复同一1086项候选，mj_forward一次，原等式/限位/禁碰/有限值/警告检查独立复算，与6878 static.json沿用原compare的atol=1e-12比较，物理阈值原样保留。要求整个积分状态及所有重载模型字段不变。禁止env.reset、compile、渲染、积分、闭合、规划、优化。

候选未修改，相机不搜索，已拒绝观察不提供模型/训练；不重跑6877/6878/6879/6880。归档日志、模型字段、复算结果并核验来源/计数；98MB MJB留在服务器，仅本地保存哈希/大小及已验证记录。本轮不能解除闭合安全拒绝或授权动力学，也不证明历史6859模型字节一致。采用executing-plans轻量执行、门禁回归测试、串行自审、verification-before-completion。
