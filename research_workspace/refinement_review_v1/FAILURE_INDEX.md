# 17 次失败逐条索引

编号为 case_方法_重复，attempt 从 1 起。所有归因均为助理证据复核，不是人工专家真值。

|运行|错误链|分类|证据说明|
|---|---|---|---|
|07_flash_new_0|object_dropped → empty_grasp → object_dropped|grasp_offset_choice_and_contact_sensitivity|新提示重复0只换候选而保留3.8cm残差；重复1同时改grasp_offset=[-0.04,0,0]与lift_height=0.25，仍掉落；重复2仅设[-0.038,0,0]成功。新规则精确XY补偿成功。 动作及结果已核验；毫米级偏移与高度的各自贡献仍需单变量验证|
|07_flash_new_1|object_dropped → object_dropped → object_dropped|grasp_offset_choice_and_contact_sensitivity|新提示重复0只换候选而保留3.8cm残差；重复1同时改grasp_offset=[-0.04,0,0]与lift_height=0.25，仍掉落；重复2仅设[-0.038,0,0]成功。新规则精确XY补偿成功。 动作及结果已核验；毫米级偏移与高度的各自贡献仍需单变量验证|
|25_flash_new_0|empty_grasp → object_dropped → object_dropped|grasp_contact_search_not_resolved|三次新提示均候选0空抓后改候选1，继而通过候选/高度/时间变化仍失败。新规则也失败；旧提示的一次XYZ微调后达到放置阶段，再修正放置成功，说明并非已证明无解。 失败模式及存在可行轨迹已核验；Z深度或夹持力原因尚未隔离|
|25_flash_new_1|empty_grasp → object_dropped → object_dropped|grasp_contact_search_not_resolved|三次新提示均候选0空抓后改候选1，继而通过候选/高度/时间变化仍失败。新规则也失败；旧提示的一次XYZ微调后达到放置阶段，再修正放置成功，说明并非已证明无解。 失败模式及存在可行轨迹已核验；Z深度或夹持力原因尚未隔离|
|25_flash_new_2|empty_grasp → object_dropped → empty_grasp|grasp_contact_search_not_resolved|三次新提示均候选0空抓后改候选1，继而通过候选/高度/时间变化仍失败。新规则也失败；旧提示的一次XYZ微调后达到放置阶段，再修正放置成功，说明并非已证明无解。 失败模式及存在可行轨迹已核验；Z深度或夹持力原因尚未隔离|
|31_flash_new_0|ik_failure → ik_failure → ik_failure|measured_xy_residual_ignored|三次均候选0→1→2并保持grasp_offset为零，约[-0.0232,-0.0433]m残差未补偿，持续approach IK失败。新旧规则的XY补偿均成功。 忽略已展示残差和对照恢复已核验；不能泛化为所有IK失败都应平移补偿|
|31_flash_new_1|ik_failure → ik_failure → ik_failure|measured_xy_residual_ignored|三次均候选0→1→2并保持grasp_offset为零，约[-0.0232,-0.0433]m残差未补偿，持续approach IK失败。新旧规则的XY补偿均成功。 忽略已展示残差和对照恢复已核验；不能泛化为所有IK失败都应平移补偿|
|31_flash_new_2|ik_failure → ik_failure → ik_failure|measured_xy_residual_ignored|三次均候选0→1→2并保持grasp_offset为零，约[-0.0232,-0.0433]m残差未补偿，持续approach IK失败。新旧规则的XY补偿均成功。 忽略已展示残差和对照恢复已核验；不能泛化为所有IK失败都应平移补偿|
|37_flash_new_0|empty_grasp → object_dropped → object_dropped|grasp_contact_search_not_resolved|三次新提示均空抓后换候选1，再改候选或lift_height仍掉落。旧提示在候选1基础上仅将grasp_offset.z设为-0.01后成功。其collision注入在首轮未触发，不应计为碰撞恢复失败。 单次Z探索成功有原始证据；仍需独立几何和种子上的可重复验证|
|37_flash_new_1|empty_grasp → object_dropped → object_dropped|grasp_contact_search_not_resolved|三次新提示均空抓后换候选1，再改候选或lift_height仍掉落。旧提示在候选1基础上仅将grasp_offset.z设为-0.01后成功。其collision注入在首轮未触发，不应计为碰撞恢复失败。 单次Z探索成功有原始证据；仍需独立几何和种子上的可重复验证|
|37_flash_new_2|empty_grasp → object_dropped → object_dropped|grasp_contact_search_not_resolved|三次新提示均空抓后换候选1，再改候选或lift_height仍掉落。旧提示在候选1基础上仅将grasp_offset.z设为-0.01后成功。其collision注入在首轮未触发，不应计为碰撞恢复失败。 单次Z探索成功有原始证据；仍需独立几何和种子上的可重复验证|
|42_flash_new_0|object_outside_container|placement_sign_and_bounds|三次面对约+0.310m的X放置残差均要求正向偏移：一次+0.31越界被拒，两次+0.25执行后出现transport IK失败；新规则先负向限幅再根据新残差修正而成功。 补偿方向解释错误和越界已直接核验；后续IK轨迹原因仅观察关联|
|42_flash_new_1|object_outside_container → ik_failure → ik_failure|placement_sign_and_bounds|三次面对约+0.310m的X放置残差均要求正向偏移：一次+0.31越界被拒，两次+0.25执行后出现transport IK失败；新规则先负向限幅再根据新残差修正而成功。 补偿方向解释错误和越界已直接核验；后续IK轨迹原因仅观察关联|
|42_flash_new_2|object_outside_container → ik_failure → ik_failure|placement_sign_and_bounds|三次面对约+0.310m的X放置残差均要求正向偏移：一次+0.31越界被拒，两次+0.25执行后出现transport IK失败；新规则先负向限幅再根据新残差修正而成功。 补偿方向解释错误和越界已直接核验；后续IK轨迹原因仅观察关联|
|47_flash_new_0|object_dropped → empty_grasp → object_dropped|mixed_grasp_transport_unresolved|首次实际错误为搬运掉落；增大lift_height后转为lift掉落或空抓，后续减速/换候选仍失败。所有方法在此条件均失败，且未到达用于注入placement故障的最终放置评估。 当前策略预算内未恢复；无证据证明场景不可解或夹持力必然是根因|
|47_flash_new_1|object_dropped → object_dropped → empty_grasp|mixed_grasp_transport_unresolved|首次实际错误为搬运掉落；增大lift_height后转为lift掉落或空抓，后续减速/换候选仍失败。所有方法在此条件均失败，且未到达用于注入placement故障的最终放置评估。 当前策略预算内未恢复；无证据证明场景不可解或夹持力必然是根因|
|47_flash_new_2|object_dropped → object_dropped → object_dropped|mixed_grasp_transport_unresolved|首次实际错误为搬运掉落；增大lift_height后转为lift掉落或空抓，后续减速/换候选仍失败。所有方法在此条件均失败，且未到达用于注入placement故障的最终放置评估。 当前策略预算内未恢复；无证据证明场景不可解或夹持力必然是根因|
