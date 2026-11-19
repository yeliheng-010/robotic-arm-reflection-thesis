# 固定新候选：完整场景静态通过，观察资格拒绝

6875生成、6876审计过的唯一候选已完成完整场景零积分恢复、attach/禁碰检查和一次固定相机资格检查。首次作业6878在收尾来源检查失败；6879独立审计在模型指纹比较失败。后续6880定位差异并复核保存观察，6881在明确MJB序列化身份条件下完成静态独立复算。**静态初态通过，观察资格拒绝；旧失败保留，闭合动力学尚未验证。**

本轮采用executing-plans轻量执行、systematic-debugging、定向门禁测试、串行源码自审和verification-before-completion。项目目录未发现独立AGENTS.md文件，执行约束来自用户本轮提供的AGENTS.md内容及原冻结方案。

## 完整场景与静态结果

保持原978505配置及相机，使用原context、model_editor和env.reset构造场景，明确跳过cv_select.scene的500步初始化。reset前已经阻断积分/环境step/闭合/规划/优化；6878记录reset=1、spec_compile=1，积分0。唯一候选SHA256为`f36b22f5fef62ce9d66feb0c9de61a0905a890e5c669a4744bdc60a55c808596`，未重新求解、修改候选或改变阈值。

完整模型nq=184、nv=152、nu=7、na=0、neq=5、nbody=71、ngeom=132；1086项完整积分状态在恢复及forward后精确保持。原机械臂、自由夹爪和手指命名/地址检查通过。历史6859未保存MJB，不能证明本次模型与历史模型逐字节相同。

|检查|6878记录及6881复算|
|---|---|
|两条connect最大绝对残差|约1.11e-16 m，原门槛1e-7 m|
|driver残差|5.6718579052178475e-11 rad，原门槛1e-7 rad|
|attach六维最大绝对残差|约2.22e-16，原门槛1e-6|
|有限关节限位|14项通过|
|接触|48条总接触，环境禁碰0、自碰撞禁碰0|
|有限值及警告|finite=true，8个警告计数均0|

6881从保存MJB独立恢复候选，沿用原inspect和compare（报告数值对照atol=1e-12，物理门槛保持），复算结果一致；所有重载模型字段以及1086项积分状态前后不变。只加载MJB一次、forward一次，环境reset、compile、积分、渲染、闭合、规划、优化均0。详见[静态复算](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_static_audit_v2/run/static.json)与[独立审计结果](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_static_audit_v2/run/result.json)。静态无禁碰不证明闭合路径安全。

## 固定相机观察仍被拒绝

全14/85%/尺寸/连通性资格保持。四个对象未通过：

|对象|可见比例|可见像素|拒绝原因|
|---|---:|---:|---|
|SortingTray|42.69%|7484|可见比例|
|PurpleCapsule|20.28%|317|可见比例、像素数|
|OrangeSphere|60.30%|442|可见比例、像素数|
|Hammer|60.10%|860|可见比例|

6878标定记录通过，475个采样、最大越界约0.424 mm，原门槛6 mm。RGB稳定检查4帧通过，post通过，eligible=true；initial比较未通过，但原规则允许稳定后post通过。观察副本隔离记录为5623字段不变。

6880只解码已保存RGB，独立复核原稳定性、initial/post及保存measurements的资格判定；没有重渲染或新采集。最后RGB像素SHA256为`f2bbbb38c7453e34c7e3b0f99dc1330fe0da4155bfad21fa5273f8a46ba54e44`。原始分割和深度数组未保存，**本轮未独立重算分割测量或标定**，只能复核已保存测量的判定。详见[原资格报告](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_candidate_v1/run/observation/qualification.json)及[保存证据复核](../qualified_scene_model_diagnostic_v1/evidence/remote/qualified_scene_model_diagnostic_v1/run/result.json)。

不合格图像没有成为项目模型或训练输入，未生成qualified_sensor.npz；没有相机搜索。3 mm深度噪声/2%缺失策略未改变，本轮未运行点云/模型链。

## 两次失败及后续独立复核

6878在观察完成后，loaded_sources拒绝5个延迟加载的PyOpenGL数组适配文件，未写result.json。6880/6881均核验其SHA256和大小与之前已冻结的PyOpenGL 3.1.10安装RECORD一致；6878仍为失败，未补写成功结果。

6879要求重载模型全部626字段完全相等，实际只有signature变化：`10107167426275082415 → 0`。6880保存了全部新字段及差异；其余625项精确相等。

核对[MuJoCo 3.3.7官方engine_io.c](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.7/src/engine/engine_io.c)、mjmodel.h、mjxmacro.h、user_model.cc：独立signature是编译模型与mjSpec之间的签名；MJB保存/加载使用的宏不包含它，模型分配清零，二进制加载不重算编译签名。安装的两个头文件与官方版本逐字节一致。pair_signature、exclude_signature仍在精确匹配范围，不作为例外。

6881是新独立的“序列化身份＋静态复算”审计：固定字段集合626项、固定原/新signature值，只允许已定位的这一个差异，其余625项精确相等；不改写内存或磁盘签名。七项测试覆盖额外参数变化、缺失/新增/更名字段、异常签名等拒绝路径。**这不等于6879原完全相等审计通过**；两次失败文件、claim、日志均保持。

## 作业和归档

|作业|内容|状态/退出码|用时|
|---|---|---|---|
|6877|入口门禁5项测试、来源登记|COMPLETED / 0:0|58秒|
|6878|零积分场景、静态及固定观察|FAILED / 1:0|40秒|
|6879|原626字段完全相等审计|FAILED / 1:0|32秒|
|6880|字段差异定位、保存RGB/资格复核|COMPLETED / 0:0|60秒|
|6881|序列化身份门禁7项测试、静态独立复算|COMPLETED / 0:0|60秒|

6877的测试主动请求了3次被阻断的积分入口和1次env.step，均在原生实现前抛错；真实积分0。prepared.json内全0是测试后的独立计数，不能声称测试从未提出积分请求。6878至6881记录的积分、闭合、规划、优化请求均为0。6880/6881分别核验8530/8544项来源，旧冻结来源、原v4失败/claim和候选保持。

62份远端证据已本地归档并逐份SHA256核验，包含本轮源码、日志、JSON/NPZ、官方参考源码及保存RGB像素PNG。模型MJB为97,903,167 bytes，SHA256=`7588512f3d6f11b9730423721e04e5106b418ef9d4a34749687de35268f1aaa0`，仅保留服务器，6880/6881实际核验；未声称本地下载。见[归档清单](../qualified_scene_model_diagnostic_v1/evidence/DELIVERY.json)、[本地最终核验](../qualified_scene_model_diagnostic_v1/evidence/FINAL_VERIFICATION.json)及[作业状态](../qualified_scene_model_diagnostic_v1/evidence/SLURM_STATUS.txt)。原scene目录audit.sbatch未提交；没有重跑旧实验、Git操作或环境安装。

## 当前阶段和下一步

完整场景零积分检查及其失败定位、独立复核已完成，综合资格不通过。生产动作仍为rejected/gripper_closure；未进行新初始化/闭合动力学、模型生成、完整抓放或训练。静态初态问题已解决到可复核层面，闭合过程会否碰撞尚未回答。

下一步建议以固定MJB和唯一候选制定有限隔离闭合诊断的新版本，明确跳过初始化、驱动时序、碰撞即停、有限步数及一次性预算，再登记后执行；本轮未启动该动力学步骤。沿用原闭合期间不重新请求视觉的协议，不因本轮观察拒绝擅自改协议或搜索相机；这些图像仍不能用于后续模型决策。
