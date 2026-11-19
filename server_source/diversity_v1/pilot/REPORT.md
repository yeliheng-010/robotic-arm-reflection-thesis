# 多样化与噪声开发试验结果

32 次任务执行已完成，16 组配对场景审计通过。

| 噪声档 | 方法 | 成功/场景 | 非法输出 |
|---|---|---|---:|
| clean | retry | 2/4 | 0 |
| clean | flash | 3/4 | 1 |
| light | retry | 2/4 | 0 |
| light | flash | 3/4 | 0 |
| medium | retry | 1/4 | 0 |
| medium | flash | 2/4 | 2 |
| strong | retry | 1/4 | 0 |
| strong | flash | 2/4 | 0 |

每次任务最多 3 次尝试，模型输出上限 1024 token。
每档仅 4 个场景，不能据此给出稳定的总体成功率或显著性结论。
对象与故障在本轮 pilot 中绑定；更完整的交叉组合仅列入 candidate_matrix.json，尚未执行。
输入深度有噪声，但错误反馈仍含仿真真值残差；没有读取封存测试集，没有导出训练标签。
RGB 场景与深度噪声拼图见 ../preflight/，逐次真实执行与模型输出见 tasks/。
