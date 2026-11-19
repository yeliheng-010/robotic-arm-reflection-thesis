# 接续开发验证记录

接续会话：`2392efee-a977-477a-b5fe-accafd4524a8`。
环境：已有 `graspnet` conda 环境，MuJoCo 3.3.7，EGL 离屏渲染。
任务：红色方块搬运到蓝色箱子。以下链接均指向本机运行产物，日志不提交到 Git。

## 真实模型链路

| 场景 | 尝试次数 | 结果 | 模型调用 / 缓存命中 | 证据 |
| --- | --- | --- | --- | --- |
| VLM 定位 + SAM + LLM 反思 + VLM 验证，首次错误定位 | 2 | 重新定位后物理与视觉均通过 | 5 / 0 | [result.json](../logs/reflection/validation/vlm_demo_v2/result.json) |
| 加高隔板，LLM 反思 + VLM 验证 | 2 | 检测真实碰撞，抬升高度改为 0.45 m 后通过 | 3 / 0 | [result.json](../logs/reflection/validation/llm_collision_first/result.json) |
| 同一隔板场景再次运行 | 1 | 命中成功经验，物理与视觉均通过 | 1 / 0 | [result.json](../logs/reflection/validation/llm_collision_second/result.json) |
| 放置位置持续偏差，规则反思 | 2 | 先落在箱外，根据残差修正后通过 | 无模型调用 | [result.json](../logs/reflection/validation/placement_v4/result.json) |

第二次隔板任务只调用视觉验证，修正来自经验数据库而非响应缓存。
完整 VLM 链路的 API 累计耗时约 13.35 秒；这是单次链路实测，不是性能统计。
模型及服务地址沿用本地配置，凭据不写入报告。

## 自然语言任务控制

- 离线指令“把绿色圆柱放进蓝色箱子”：实际执行对象是 `GreenCylinder`，首次物理验证通过。
  [结果记录](../logs/reflection/validation/natural_language_green/result.json)。
- 自由中文“请帮我把那根绿色的圆柱形物体收进蓝色盒子里”：LLM 解析为
  `GreenCylinder -> BlueBin`，首次物理验证和 VLM 验证通过。
  [结果记录](../logs/reflection/validation/natural_language_llm_green/result.json)。
- 上述语言任务使用仿真感知与几何抓取；LLM 任务解析、图像感知、失败反思分别配置和记录。
- 新增语言测试 6 项通过，覆盖中英文对象选择、否定/歧义/多任务拒绝、显式参数冲突、
  模型返回类型与场景约束、实际执行参数传递、交互输入和已有日志保护。

## 四组受控对比

规则反思、仿真分割、几何抓取，三个持续故障：标定偏差、隔板碰撞、放置偏差。
每个条件运行两次，共 24 个任务；各方法使用相同配对种子 42、43。
这里只比较闭环机制，不是 LLM 对比实验。

| 方法 | 任务成功数 | 首次任务平均尝试 | 后续任务平均尝试 | 后续任务平均耗时 |
| --- | --- | --- | --- | --- |
| baseline | 0 / 6 | 1 | 1 | 9.50 s |
| retry | 0 / 6 | 3 | 3 | 28.46 s |
| reflection | 6 / 6 | 2 | 2 | 22.45 s |
| reflection_memory | 6 / 6 | 2 | 1 | 13.02 s |

记忆组在三个后续任务中均实际命中经验，首次任务均无经验。
物理成功与接受成功在此次离线运行中一致，没有开启视觉模型验证。
数据：[episodes.csv](../logs/reflection/validation/final_benchmark/episodes.csv)、
[summary.json](../logs/reflection/validation/final_benchmark/summary.json)、
[comparison.png](../logs/reflection/validation/final_benchmark/comparison.png)。

复现命令（使用新的输出目录）：

```bash
conda activate graspnet
MUJOCO_GL=egl python -m experiments.run_benchmark --episodes 2 \
  --faults calibration collision placement --output logs/reflection/benchmark_reproduction
```

## 自动验证

- 新增反思测试 8 项通过：动作顺序、目标约束与非法字段、定位/深度/mask、非法修正、记忆隔离与降级、视觉返回类型、物理支撑与完整包含。
- 原抓取流水线测试 10 项通过。
- 结果图像已人工检查，成功记录中的方块实际位于箱内。

## 先显示场景与一键实验

- `--interactive` 默认先创建并稳定场景，再等待终端输入；输入、执行、重试共用窗口。
  在同一进程依次输入绿色圆柱、红色方块入蓝箱，两次均首次物理成功；退出后窗口关闭。
  记录：[圆柱](../logs/reflection/validation/scene_first/task_003/result.json)、
  [方块](../logs/reflection/validation/scene_first/task_004/result.json)、
  [窗口截图](../logs/reflection/validation/scene_first/reflection_scene_after_two_tasks.png)。
- 修复多渲染器释放资源时破坏其他深度渲染器的问题，增加实际 RGB-D 渲染回归测试。
- `bash run_experiments.sh` 实际完成 24 个无头任务，初始位置每轴在 +/- 8 mm 内扰动。
  baseline 和 retry 各 0/6 成功，规则 reflection 和 reflection_memory 各 6/6 成功。
  三个记忆后续任务均命中经验并首次成功。此处没有模型 API 调用，不能作为 LLM 实验结论。
  [运行报告](../logs/reflection/validation/automated_smoke_final/REPORT.md)、
  [跨阶段 CSV](../logs/reflection/validation/automated_smoke_final/suite_episodes.csv)、
  [分条件汇总](../logs/reflection/validation/automated_smoke_final/smoke/summary_by_fault.csv)。
  已核对 24 个唯一任务、45 次尝试，CSV、JSON、种子和图像路径一致。
- smoke、pilot、thesis 的矩阵分别为 24、336、1120 个任务，thesis 的 dry-run 数量已核对。
  pilot 的模型凭据、SAM 权重和离屏渲染预检通过；没有执行整套 pilot / thesis。
- 反思、语言、实验测试共 23 项通过，原抓取流水线 10 项通过。
  包含中断任务的 SQLite 回滚、服务错误单独保存、配置不匹配拒绝续跑和子进程退出检查。
- 另运行 12 任务的小矩阵，在第六任务中断后使用 `--resume` 完成 12/12。
  前五个任务直接加载已完成结果，未重新执行；第六任务从初始状态重跑。
  [续跑报告](../logs/reflection/validation/suite_resume/REPORT.md)。

实验设计与采样边界见 [PROTOCOL.md](../experiments/PROTOCOL.md)。

## 解释边界

四组实验的默认反思器是规则实现，只用于验证闭环机制与对照流程。
真实模型结果单独列出，不将规则实验包装成 LLM 实验。
检测中的分割归属、物体接触身份和位置残差包含仿真真值；结果验证使用独立物理检查。
失败重试恢复相同初始场景，因此不代表真机掉落后的原地恢复能力。
小规模固定场景复测不能支持论文中的统计显著性或跨场景泛化结论。

运行方法和实验选项见 [README.md](README.md)。

## 提示词去除先验后的复测（2026-10-08）

上文的模型结果使用的是旧提示词，其中反思提示写有"碰撞且接触隔板时考虑 0.45 m 抬升"，
规划提示直接给出了源物体与目标的 body 名称和标准动作模板。现已改为：

- 反思提示（`reflect-v2`）只说明参数含义、取值范围和证据字段含义，不给出错误到修正的对应关系；
- 规划提示（`plan-ground-v3`）只给自然语言指令和场景图像，由模型自行选择并定位物体，
  物体名称通过开放词汇映射到场景 body，选错物体会被 `validate_plan` 检测为 `plan_wrong_object`。

复测（Qwen3.5-397B-A17B，关闭响应缓存，每项各运行 1 次）：

| 条件 | 结果 | 模型给出的修正 |
| --- | --- | --- |
| 隔板碰撞，仿真感知 + LLM 反思 | 2 次尝试成功 | `lift_height` 0.35 → 0.48 |
| 标定偏差，仿真感知 + LLM 反思 | 2 次尝试成功 | 根据 -0.042 m 的 y 残差设置 `grasp_offset` y=+0.04，并调整速度与抬升高度 |
| 放置偏差，仿真感知 + LLM 反思 | 2 次尝试成功 | 根据约 -0.18 m 的 x 残差设置 `place_offset` x=+0.20 |
| 无注入故障，完整 VLM 规划/定位 + SAM，4 条中文指令 | 4/4 成功；紫色胶囊入红箱首次落在箱外，反思后成功 | 根据残差设置 `place_offset` (-0.05, -0.04, 0) |

在新提示词下，"把红色方块放进蓝色箱子"被正确定位到方块上，旧流程（`vision_agent` 提示词）中
反复出现的"把红色方块定位到红色箱子"错误没有复现。紫色胶囊的放置失败没有注入任何故障，
属于自然产生的错误。以上每项只运行 1 次，用于确认去除提示后闭环仍然有效，不作为统计结果。
