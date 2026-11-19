# 串行源码核对与风险边界

1. `qualified_closure_dynamics_v3/entry.py:run_environment`和旧v1入口调用opened，切换setup阶段，强制setup_steps==500，然后initial.prepare；这条路径必须替换，不能用setup预算0但继续调用旧入口。
2. 旧`initial.prepare`会place_robot、清零速度/热启动/外力并覆写ctrl；新候选已经完成初态构造及6角投影，不能再次变换。新入口只能restore已冻结完整integration。
3. 原ur5_grasp_env.py的step写ctrl，mj_step一次；只有viewer非None才sync。新直接MJB后端可保持这两句物理语义，不需要创建环境、机器人或渲染器。TCP诊断原tool平移是[0,0,0.13]，必须从冻结源码绑定，不能凭新机器人默认值。
4. 原worker每步先意图后积分，再observe和判停；要保留调用未返回的uncertain_step。旧StepGate在调用原生前计数，只能表示requests，不能直接当成确定完成数；新版本必须分开requests/returns。
5. capture.observe复制原缓存并只forward副本，验证live状态/缓存不变，可复用。旧Backend依赖env/robot，不能直接套用；只复用reference_vectors和采集规则。
6. 旧audit.trace_contract硬编码setup=500，main也将重载模型与编译指纹比较；必须独立新版本改为setup=0、6881重载626字段基线，而非放宽旧审计。
7. 完整物理步进是明确行为变更，后续入口采用新增替身TDD/回归、代码自审和完成前验证；本轮只增加方案校验器，不运行动力学，采用定向核验即可。指定子代理型号不在当前可用列表，本轮串行，不委派。
8. 98MB模型每步指纹与落盘可能接近120秒墙钟预算。保持原预算，超时如实停止，不追加“为完成1000步”而放宽预算。不得在本轮运行真实性能试轨迹。
9. 视觉不合格与静态初态合格分别记录。私有动力学诊断不调用模型、不重新采集，不授予生产或训练准入。无碰撞的单条离散轨迹仍不足以解除旧包络拒绝。

本轮校验只能证明方案输入与既有证据自洽、来源未变，不能证明尚未实现的动力学入口或新审计正确。
