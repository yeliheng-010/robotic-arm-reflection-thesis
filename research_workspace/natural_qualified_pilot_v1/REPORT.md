# 资格后能力小批结果

5933 COMPLETED / 0:0；11条件，25次尝试，0模型调用。逐条件完整独立审计通过。

- baseline首次/最终均2/2。
- varied_noisy首次/最终均2/9（C1_962701、C0_962707）；0恢复。
- 5936 COMPLETED / 0:0，3项盘点测试通过；14条决策去重后4个自然失败快照，来自962703/962708，0实际自然恢复。
- 排除6条grounding_off_target、2条grounding_out_of_image、2条planning rejection决策。多数失败在定位/规划阶段，不能充当自然掉落恢复样本。

两个掉落现场的三次尝试均已耗尽。真实记录显示闭爪阶段曾双侧接触目标，末端夹爪垫位置靠近源物体上缘。-10mm、3倍时间未恢复；不能把这些证据直接升级成唯一因果结论。

下一步：新种子先做观测资格，再验证更深抓取偏移。原图像/NPZ/完整审计多数仍在服务器。本地最终complete及inventory、作业日志的交付哈希见qualified_data_review_v1/LOCAL_DELIVERY.json。全部属于pilot，正式训练门槛未达到。
