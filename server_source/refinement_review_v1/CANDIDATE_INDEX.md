# 成功转移候选复核

以下不是训练文件：所有条目 training_approved=false。模型与专家分开，保留原始解释及其缺陷。

|候选|来源|后继物理成功|复核状态|标记|
|---|---|---|---|---|
|07_flash_new_2/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|07_flash_old_2/a2|llm|True|physical_action_candidate_only|解释称更居中，但按当前XY残差与新减旧偏移计算，线性残差范数反而增大；物理稳定性成功不证明这句解释正确|
|07_rule_new_0/a1|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|07_rule_old_0/a1|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|11_flash_new_0/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|11_flash_new_1/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|11_flash_new_2/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|11_rule_new_0/a2|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|11_rule_old_0/a2|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|22_flash_new_0/a1|llm|True|separate_exploration_candidate|放置残差缺失；正X探测依赖明确写出的猜测，应与有测量依据的补偿分组|
|22_flash_new_1/a1|llm|True|separate_exploration_candidate|放置残差缺失；正X探测依赖明确写出的猜测，应与有测量依据的补偿分组|
|22_flash_new_2/a1|llm|True|separate_exploration_candidate|放置残差缺失；正X探测依赖明确写出的猜测，应与有测量依据的补偿分组|
|22_flash_old_1/a2|llm|True|physical_action_candidate_only|candidate_index 被描述为放置姿态候选，作用范围表述有歧义；实际参数选择抓取姿态|
|22_rule_new_0/a2|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|23_flash_new_0/a2|llm|True|physical_action_candidate_only|长解释多次颠倒目标与残差后给出正确公式，动作有效但原始反复推导不宜直接用于训练|
|23_flash_new_1/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|23_flash_new_2/a2|llm|True|physical_action_candidate_only|解释称当前只能调整位置参数，但候选和时间参数也可用；存在能力边界表述错误|
|23_flash_old_0/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|23_rule_new_0/a2|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|25_flash_old_1/a2|llm|True|physical_action_candidate_only|将X残差-0.062375m称为约-6.2mm，存在约10倍单位换算错误|
|30_flash_new_0/a1|llm|True|physical_action_candidate_only|解释含负残差下正偏移使指令点进一步远离物体的错误陈述；最终动作成功不验证该陈述|
|30_flash_new_1/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|30_flash_new_2/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|30_flash_old_1/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|30_rule_new_0/a1|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|31_rule_new_0/a1|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|31_rule_old_0/a1|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|32_flash_new_0/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|32_flash_new_1/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|32_flash_new_2/a1|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|32_flash_old_2/a1|llm|True|physical_action_candidate_only|解释先颠倒残差方向后自我修正，不宜把未经整理的整段反复推导作为高质量目标文本|
|32_rule_new_0/a1|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|37_flash_old_0/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|42_rule_new_0/a2|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_flash_new_0/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_flash_new_1/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_flash_new_2/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_flash_old_0/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_flash_old_1/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_flash_old_2/a2|llm|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
|44_rule_new_0/a2|rule_expert|True|physical_action_candidate_only|未发现明显参数语义错误；因果解释未经验证|
