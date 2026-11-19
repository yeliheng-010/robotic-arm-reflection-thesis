# 定向监督数据包

已重新审计24个条件、214次物理执行，重建45个决策输入并核对原记录。

| 文件 | 输入数 | 用途 |
|---|---:|---|
| positive_sets.jsonl | 30 | 所有成功输入，保留完整已观察成功动作集合 |
| single_success_sft.jsonl | 23 | 单成功聊天格式；与single_success.jsonl逐行对应 |
| multi_success.jsonl | 7 | 多成功集合，不任意选一个为唯一答案 |
| unresolved.jsonl | 15 | 已测试分支未成功，不推断未试候选 |
| provenance.jsonl | 45 | 原始输入、分支结果和物理证据索引 |
| quarantine.jsonl | 0 | 当前无旧输入重合；后续重合进入隔离 |

文件是同一数据的不同视图，不能相加。30个正例输入对应38个已观察成功动作，不是38个独立样本。
23个单成功输入中13个立即成功、10个经后续规则修正才最终成功。
数据来自6个新训练种子组，model=null，来源为规则分支搜索；未使用预留测试。

## 语义与来源

messages保持原选择器输入，不加入隐藏故障值、结果标签或额外审计信息。
accepted_action_ids只覆盖已测试的成功动作；observed_unsuccessful_action_ids只表达该规则后续策略下的失败。
untested_action_ids表示未测试，不能作为负例。tested_outcomes保留立即/终局成功、后续尝试数、轨迹路径与hash。
单成功是“目前只观察到一个成功动作”，不等价于全候选空间唯一正确。

## 验证

```json
{
  "passed": true,
  "inputs": 45,
  "positive_inputs": 30,
  "successful_action_observations": 38,
  "counts": {
    "positive_sets": 30,
    "single_success": 23,
    "multi_success": 7,
    "unresolved": 15,
    "quarantine": 0
  },
  "single_sft_rows": 23,
  "single_timing": {
    "delayed": 10,
    "immediate": 13
  },
  "positive_groups": [
    "targeted_collection_v1:930001",
    "targeted_collection_v1:930002",
    "targeted_collection_v1:930003",
    "targeted_collection_v1:930004",
    "targeted_collection_v1:930005",
    "targeted_collection_v1:930006"
  ],
  "training_started": false,
  "test_used": false,
  "original_training_inputs": 159,
  "original_train_overlap_with_expanded_dev": 0,
  "held_input_count": 212,
  "exact_new_overlap_with_old_train": 0,
  "exact_new_overlap_with_dev": 0,
  "source_conditions": 24,
  "source_physical_executions": 214,
  "new_physical_executions": 0,
  "original_training_modified": false,
  "source": "expert_counterfactual_rule_continuation",
  "model": null
}
```

## 训练建议（未执行）

建议主方案保留30个输入的成功动作集合；7个多解输入包含新增的候选切换、深度、减速和下降−90°成功证据。
旧159条加单成功23条可作为182输入的消融方案；主方案159+30为189逻辑输入，需先核定并实现多正例训练目标。
如将每个成功动作展开成单条回复训练，建议每个原输入总权重相同（每回复权重1/k），避免多解输入被重复加权。
该权重策略尚未实现到原训练器，不能将集合文件直接交给原单标签训练脚本。也不以字符串完全匹配惩罚其他已验证成功动作。
原159条标签是立即整体成功，新集合含延迟成功，须保留来源与语义，并分别报告相应效果。
暂不修改原159条、训练参数、模型或开发/测试划分；本轮没有启动训练或新增物理实验。
