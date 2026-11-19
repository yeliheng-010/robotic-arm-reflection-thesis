# 定向试采结果

处理24/24个条件，合格24，跳过0。
独立物理执行214/240次，模型调用0。

监督候选统计：
```json
{
  "raw_nodes": 45,
  "unique_inputs": 45,
  "eval_overlap": 0,
  "single_success": 23,
  "multiple_success": 7,
  "no_success": 15,
  "contradictory_observations": 0,
  "old_train_overlap": 0
}
```

规则分支搜索数据，非模型生成数据。成功动作集合仅覆盖已试分支，后续策略固定为规则。
同输入多解、矛盾与开发重合保留并标记；未自动导出SFT或启动训练。
