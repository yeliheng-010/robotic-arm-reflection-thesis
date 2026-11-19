# 入口修订审查

6006确认并保留旧路径反例：`import freeze,smoke,train`在vf_common永久插入candidate目录后，smoke/train解析为旧文本入口；5997七项逻辑测试仍有效，但它的入口检查不足以证明新入口正确。

修订仅新增文件，原冻结已有文件不改：vf_common_v2在加载已验证runtime/loss后恢复sys.path；train_v2明确引用smoke_v2。6006七项逻辑测试通过，四个v2模块实际路径逐个断言通过，train_v2.probe is smoke_v2.probe成立。未来只运行freeze_v2.sbatch/train_v2.sbatch。

原衔接监控6001已取消，仅当时collecting，没有提交训练链。training_stage_bridge_v2的6007五测试与源身份冻结通过，测试确认训练依赖v2冻结，冻结同时依赖正式编码审计和基础模型对照；新watch待启动/核对实际作业ID。5974仿真未被打断。后续旧监控不可恢复。

6003真实两图反向检查通过：496个有限梯度张量，norm6.6163，峰值显存9.33GB，参数逐张量保持不变，0优化器更新。仍未执行真实smoke更新、adapter保存重载或正式训练，数据门槛尚未达标。
