# Flash-Next 机械臂反思接入

将服务器共享的 `qwen3.8-flash-next` 接入已有 UR5e 仿真错误反馈流程：

任务执行 → 错误证据 → Flash-Next 返回 cause / changes → 参数校验 → 使用新参数恢复同一场景重试 → 物理验收。

## 当前运行

- 服务：`http://127.0.0.1:8080/v1`，由管理员的 `local-llm` / `gpu-lender` 管理。
- 模型：Flash-Next GSQ-RCO IQ3_S，CPU 与 GPU 混合运行；没有重新微调模型。
- 接入：`client.py` 的 `FlashReflector`，可作为原执行器的 reflector。
- 离线评估：Slurm 4518，冻结 validation 的 294 条，输出上限 256 token。
- 闭环评估：Slurm 4519，6 个开发场景 × retry / rule / flash 三组，共 18 次任务执行，每次最多尝试 3 次；Flash 输出上限 1024 token。
- 三类开发例：3/3 合法，1/3 严格匹配；只作为接口冒烟证据。
- 首个闭环开发场景（红色方块到黄色托盘，calibration）：retry 3 次均失败；rule 和 flash 各 2 次成功。Flash 实际生成并执行 `grasp_offset=[0,0.042,0]`；原始输出、实际参数和同场景配对审计通过。
- 完整结果待作业结束后核验；本文件不把已提交作业计作已完成。

## 在执行器中使用

服务器运行目录为 `/home/yeliheng/grasp_server/improvement_20261019/code`，将本包父目录、原 stability 和 geometry 包父目录加入 PYTHONPATH。

```python
from flashnext.client import FlashReflector
from stability.loop_worker import engine_class

reflector = FlashReflector(instruction, output_directory, max_tokens=1024)
engine = engine_class()(reflector=reflector, max_attempts=3,
                       headless=True, task_parser='rule', scene_jitter=.012)
try:
    result = engine.run(**task, instruction=instruction,
                        output=output_directory, method='reflection',
                        context='flashnext-development')
finally:
    engine.close()
```

仿真须在 Slurm 分配的 GPU 作业内运行。模型端点由共享服务负责，不在仿真脚本里另启 GPU 推理进程。

## 行为与证据边界

- 保持已有提示：仅传文本错误证据和历史；不使用图片，不声称验证了视觉能力。
- 严格校验未知字段、数值范围、未变化参数、候选索引、生成截断和返回模型身份。
- 无规则回退、无 JSON 修补；失败保留原始响应及原因，并进入失败分母。
- 每次模型请求和响应写入 `requests.jsonl`，执行轨迹保留实际参数、初始状态和物理验收。
- 验证集标签来源是 `rule_expert`；模型的参数严格匹配率不能等同于机器人成功率。
- 闭环是 6 场景开发评估，不是封存测试；输入包含仿真真值残差。1024-token 闭环不能与历史 256-token 模型结果做同预算比较。
- 216 条封存 test 不读取，不用于调参，也不导出本轮输出为训练数据。

## 服务器结果路径

根目录：`/home/yeliheng/grasp_server/flashnext_v1`。

| 路径 | 内容 |
|---|---|
| `smoke256/` | 三类开发例请求与回答 |
| `validation256/progress.json` | 离线评估进度 |
| `validation256/responses.jsonl` | 逐样本原始请求、回答与指标 |
| `validation256/result.json` | 离线评估最终状态 |
| `closed_loop1024/progress.json` | 闭环三组进度 |
| `closed_loop1024/tasks/` | 实际物理轨迹、图像和模型调用 |
| `closed_loop1024/audits.json` | 已完成场景的参数执行与配对审计 |
| `delivery_verification.json` | 两个作业结束后独立核验结果 |
| `RESULTS.md` | 独立核验通过后自动生成的最终汇总 |

脚本拒绝覆盖已有结果目录。再次实验必须使用新的输出目录并冻结协议，不直接重复提交本轮脚本。

技能：test-driven-development；verification-before-completion。关键边界测试已在模型与仿真 Python 环境各执行一次，均为 3/3 通过。

