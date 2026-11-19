# UR5e 错误反馈与智能反思

接续 Claude 会话 `2392efee-a977-477a-b5fe-accafd4524a8`。
原始会话位于 `/home/yeliheng/.claude/projects/-home-yeliheng---/2392efee-a977-477a-b5fe-accafd4524a8.jsonl`。
已确认需求：MuJoCo、规划/感知/执行/放置四类错误、大模型反思、经验记忆、VLM 验证和四组对比实验。

已运行的模型闭环、经验复用和对照结果见 [VALIDATION.md](VALIDATION.md)。

## 启动

在 `VLM_Grasp_Interactive` 根目录使用已有 `graspnet` 环境：

```bash
conda activate graspnet
# 离线物理闭环：加高隔板，检测碰撞，反思增加抬升高度
python -m reflection --fault collision --method reflection_memory
# 原生 MuJoCo 窗口
python -m reflection --fault collision --viewer
# 再次运行同一场景，验证首次尝试前读取经验
python -m reflection --fault collision --method reflection_memory --output logs/reflection/demo_second
```

默认使用规则反思、仿真分割和几何抓取，便于无需 API 验证软件与物理链路。
这些默认结果不是 LLM 能力实验。首次尝试前默认参数不包含故障类型。
`--context` 标识外部可观测的实验配置/标定会话。不同配置请使用不同 context，防止经验误用。

## 自然语言控制

`--instruction` 现在会先解析出实际物体与容器，再执行任务，结果中保存 `task_resolution`。
不传指令时仍默认把红色方块放进蓝色箱子。指令与显式 `--source` / `--destination` 冲突时拒绝执行。

```bash
# 常见明确指令：离线解析，无需模型 API
python -m reflection --instruction "把绿色圆柱放进蓝色箱子" --fault none \
  --viewer --context normal-control --output logs/reflection/language_01

# 连续输入自由中文指令：调用模型解析任务与反思，并用 VLM 验证结果
python -m reflection --interactive --task-parser llm --reflector llm --visual-verify \
  --fault none --viewer --context normal-control --output logs/reflection/chat

# 单次错误反馈演示：不预加载记忆，观察碰撞后 LLM 修改参数
python -m reflection --instruction "把红色方块放进蓝色箱子" --task-parser llm \
  --fault collision --method reflection --reflector llm --visual-verify --viewer \
  --context collision-demonstration --output logs/reflection/collision_llm_01
```

交互模式默认先打开仿真窗口，场景稳定后才在终端等待指令。输入 `exit` 或 `退出` 结束。
执行、重试和下一条输入共用同一窗口；每次等待新指令前恢复初始场景。
每次任务使用独立的 `task_001` 等目录，重新启动时跳过已有目录。
这不是在同一已改变场景中持续操作。无图形界面时显式传 `--headless`，可继续终端交互。

```bash
# 先看环境，再输入明确指令，无需 API
python -m reflection --interactive --fault none --task-parser rule
```

当前可操作物体：红色方块、绿色圆柱、紫色胶囊、橙色小球。
目标容器：蓝色箱子、红色箱子、黄色托盘。支持一个物体搬运到一个容器，
不能执行多物体连续任务、堆叠、任意坐标移动或未实现的附加约束。
任务解析成功不保证抓取成功，失败依然按错误反馈闭环记录。

`--task-parser auto` 默认先解析明确的中英文搬运句式；已有模型客户端时，复杂措辞再交给 LLM。
没有客户端时无法解析会报错，可指定 `--task-parser llm` 启用模型。
`--task-parser rule` 只做离线解析；`--task-parser llm` 始终调用模型解析任务。
这与 `--perception vlm` 的图像规划/定位、`--reflector llm` 的失败诊断是不同功能。
普通语言控制请显式使用 `--fault none`，原有默认 `collision` 会主动加高隔板以制造碰撞。

ModelScope 使用根目录 `.env` 中已有的 `MODELSCOPE_API_KEY`、`MODELSCOPE_MODEL_ID`、
`MODELSCOPE_BASE_URL`，可通过 `REFLECTION_MODEL_ID` 单独选择反思模型。
模型不可用或返回非法修正时记录错误并停止该次反思实验，不自动混入规则结果。

```bash
# 真实大模型反思 + VLM 前后图像判断，感知仍使用仿真真值
python -m reflection --fault collision --reflector llm --visual-verify --context llm-session
# 完整 VLM 规划/定位 + SAM + 大模型反思 + VLM 验证
python -m reflection --fault grounding --reflector llm --perception vlm \
  --segmentation sam --visual-verify --context vlm-session --output logs/reflection/vlm_demo
```

SAM 和 GraspNet 复用已有权重和安装环境；`--grasp-backend hybrid` 可使用原 GraspNet/几何回退。

## 一键论文实验

完整方案见 [experiments/PROTOCOL.md](../experiments/PROTOCOL.md)。在项目根目录运行：

```bash
bash run_experiments.sh                         # 24 个离线任务，检查流程
bash run_experiments.sh --profile pilot         # 336 个任务，模型预实验
bash run_experiments.sh --profile thesis --dry-run  # 预览 1120 个任务的矩阵
bash run_experiments.sh --profile thesis --stages mechanism
bash run_experiments.sh --profile thesis --stages integrated verification_ablation
bash run_experiments.sh --resume logs/reflection/experiments/上次运行目录
```

默认使用 EGL 无头模式，仍保存相机图像。新运行自动分配目录和经验库；启动时显示输出路径。
每个任务完成后导出 CSV，中断后可续跑。API 服务异常保存为 `service_error.json` 并停止，
修复服务后续跑该任务；非法模型输出作为方法失败记录。正式模型实验关闭响应缓存。
`suite_episodes.csv` 汇总各阶段的任务，`suite_summary_by_fault.csv` 按条件汇总，
各阶段还有 `attempts.csv`、图表、每次尝试的错误证据、反思参数和图像。
无显示器时默认选择 EGL。如果主机未提供 EGL，可按本机配置设置 `MUJOCO_GL=osmesa`。

## 四组实验

```bash
# 快速检查：3 个持续故障 x 4 种方法 x 2 次任务，共 24 个任务
python -m experiments.run_benchmark --episodes 2 --faults calibration collision placement \
  --output logs/reflection/benchmark_rule_01
# 相同条件下的大模型实验：VLM 规划/定位 + SAM + LLM 反思 + VLM 验证
REFLECTION_LLM_CACHE=0 python -m experiments.run_benchmark --episodes 2 \
  --faults calibration collision placement --reflector llm --perception vlm \
  --segmentation sam --visual-verify --output logs/reflection/benchmark_llm_01
```

先用 2 次检查流程，再将 `--episodes` 增加到 10 等所需数量。
批量实验默认不开窗口；结果位于 `--output` 指定的目录，输出目录必须使用新的名称。
`--faults` 可另选 `planning`、`grounding`、`slip` 等条件；`--sources` 可选择多个场景物体。

`baseline` 只有一次尝试；`retry` 在预算内不改参数；`reflection` 根据证据修改参数；
`reflection_memory` 仅把独立物理验证成功的修正写入 SQLite，并在后续任务前应用。
每组使用配对随机种子、相同任务和故障条件。每个条件独立创建数据库，区分首个任务
`cold` 和后续任务 `subsequent`，并单独记录实际 `memory_hit`。输出目录不可复用，避免覆盖结果。

输出包括 `episodes.csv`、`summary.csv`、`summary.json`、`comparison.png`，以及每次任务的
`result.json`、规划、mask、前后图像、结构化错误、反思原因和应用参数。
统计包含成功率、物理成功率、尝试次数和耗时；成功率给出 Wilson 区间，
但重复的固定场景不是独立抽样，小规模结果不能证明统计显著性。

## 故障和证据

| 故障参数 | 真实作用位置 | 主要证据 |
| --- | --- | --- |
| `planning` | 首次尝试损坏动作序列 | 规划时序校验 |
| `grounding` | 首次定位改为红色箱子像素 | 相机分割归属 |
| `calibration` | 持续向抓取坐标施加 -4.5 cm 的 y 偏差 | 指垫接触、抓取残差 |
| `collision` | 在编译前把隔板加高到 38 cm | 搬运中的真实接触 |
| `slip` | 首次搬运时把夹爪控制命令置为张开 | 双侧接触丢失超过 0.2 秒 |
| `placement` | 持续施加 -17 cm 的放置 x 偏差 | 最终物体和容器的残差 |
| `unreachable` | 持续施加 +15 cm 抓取 x 偏差 | IK 异常或空抓 |

注入不改成功标志、不吸附物体，也不伪造检测结果。模型修正限定在重新规划/定位、
有限抓取与放置偏移、抬升高度、速度和候选索引，非法参数不会执行。
物理评估要求物体整体水平边界在容器内部、高度合理、与容器接触、速度稳定；
绿色圆柱还要求姿态未倾倒。VLM 判断单独保存；图像遮挡时允许 `null`，API 错误明确标记。
`success` 表示物理通过且没有视觉否决；视觉服务不可用不会覆盖独立的 `physical_success`。

## 实验边界

- 本实现是受控仿真试验：每次失败后恢复相同初始场景，再以修正参数重新执行。
  日志标注 `restore_same_initial_scene_each_attempt`。这不等同于真机在掉落后原地恢复；
  在真实机器人上需要额外的安全撤离、重新感知和恢复控制器。
- 分割归属、指垫接触的物体身份、抓取残差和放置验证来自仿真真值。
  即使选择 VLM/SAM，这些检测证据仍属仿真辅助，不能宣称已经完成纯视觉真机检测。
- 默认几何后端通常只有一个候选；换候选不能保证修复所有不可达位姿或物体形状。
  所有支持物体都可运行，但不保证所有任务成功，失败会保留证据。
- 当前支持自然语言指定单物体搬运到已知容器，未扩展多物体开放指令和执行途中的自然语言人工纠错。
- 模型响应缓存与经验记忆是不同的 SQLite 数据库。缓存命中记录在客户端统计里；
  耗时实验应单独报告缓存状态，或设置 `REFLECTION_LLM_CACHE=0`。

## 测试

```bash
python -m unittest discover -s tests -p 'test_reflection*.py' -v
python -m unittest discover -s tests -p 'test_grasp_pipeline.py' -v
```
