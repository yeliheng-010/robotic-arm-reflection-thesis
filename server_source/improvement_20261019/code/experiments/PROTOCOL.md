# 论文实验方案与自动运行

论文：基于机械臂的错误反馈与智能反思系统。
平台：UR5e + Robotiq 夹爪，MuJoCo 仿真；使用现有抓取流水线。

## 研究问题

1. 检测到错误后，根据证据修正参数，是否比不修改参数的直接重试更有效？
2. 独立验证成功的经验是否提高同类后续任务的首次成功率，减少尝试与耗时？
3. 图像规划、分割、反思与验证串联后，闭环是否仍有效？视觉验证是否产生否决或无法判断？

## 对照组

| 方法 | 尝试预算 | 失败后的处理 | 经验记忆 |
| --- | --- | --- | --- |
| baseline | 1 | 停止 | 无 |
| retry | 3 | 不改参数，恢复初始场景后再试 | 无 |
| reflection | 3 | LLM 根据错误证据修正参数 | 无 |
| reflection_memory | 3 | LLM 修正；后续任务先检索经验 | 只保存验证成功的修正 |

baseline 是一次执行的参考。评价反思效益主要比较同预算的 retry 和 reflection；
评价记忆主要比较 reflection 与 reflection_memory 的后续任务。
各组使用相同物体、目标、故障、配对场景种子和抓取后端。首次任务无记忆，后续任务另报实际命中率。
同一故障条件对应独立的可观测标定/布置会话，不向反思器传递隐藏的故障名称。

## 任务与错误条件

主实验使用红色方块与绿色圆柱，目标为蓝色箱子。圆柱额外要求不倾倒。
其他物体可作为后续扩展，不能仅因支持名字就假定抓取成功。

| 条件 | 阶段 | 注入机制 | 解释 |
| --- | --- | --- | --- |
| none | 对照 | 不注入故障 | 正常场景可靠性 |
| planning | 规划 | 首次动作顺序损坏 | 重试也可能恢复，不能单凭成功归功于反思 |
| grounding | 感知 | 首次定位到其他物体 | 同上，属于瞬时错误 |
| calibration | 执行 | 持续抓取位置偏差 | 用于检验参数补偿 |
| collision | 执行 | 持续加高隔板 | 用于检验搬运轨迹参数修正 |
| slip | 执行 | 首次搬运时张开夹爪 | 真实接触丢失检测；属于瞬时错误 |
| placement | 放置 | 持续放置位置偏差 | 用于检验最终位置残差补偿 |

每个任务按种子对目标物体初始 x/y 位置做小幅扰动，默认各轴在 +/- 8 mm 内。
同一任务的重试恢复完全相同的扰动；同一种子在所有方法和视觉消融中配对。
这提供局部场景变化，不能代表开放世界泛化。

## 自动实验阶段

| 阶段 | 反思 | 感知 / 分割 | VLM 结果验证 | 用途 |
| --- | --- | --- | --- | --- |
| smoke | 规则 | 仿真 / 仿真 | 关闭 | 无 API，检查运行和导出流程 |
| mechanism | LLM | 仿真 / 仿真 | 关闭 | 隔离反思与经验记忆的影响 |
| integrated | LLM | VLM / SAM | 开启 | 验证完整多模态闭环 |
| verification_ablation | LLM | VLM / SAM | 关闭 | 与 integrated 配对，研究视觉否决与未知判断 |

批量实验的任务目标由实验矩阵固定，不额外调用自然语言解析器，以免引入语义解析混杂。
自然语言交互演示是独立功能，不能替代批量数据。

| 一键配置 | 物体 | 条件数 | mechanism 次数/条件 | integrated / 消融次数/条件 | 总任务数 |
| --- | --- | --- | --- | --- | --- |
| smoke | 红色方块 | 3 个持续故障 | 不运行 | 不运行 | 24（规则，2 次/条件） |
| pilot | 方块、圆柱 | 7 | 2 | 各 2 | 336 |
| thesis | 方块、圆柱 | 7 | 10 | 各 5 | 1120 |

先运行 smoke，再运行 pilot 检查模型服务、权重、失败案例和运行耗时，最后运行 thesis。
thesis 是建议采样规模，不承诺统计显著性。预计需要大量模型调用，可用阶段筛选分批完成。
脚本固定关闭模型响应缓存；经验记忆仍按方法启用，二者不能混淆。

## 数据与评价

- 主指标：独立物理成功率，要求完整入箱、容器支撑、稳定，圆柱保持直立。
- 次指标：接受成功率、首次尝试成功率、初次失败后的恢复率、尝试次数、总耗时。
- 记忆指标：cold / subsequent 分开，报告实际命中率和后续任务首次成功率。
- 反思证据：每次错误的阶段、类型、接触/位置残差、模型诊断、建议参数、应用参数与结果图像。
- 视觉结果：true / false / unknown / API 错误分别记录。物理通过但 VLM 否决与物理失败不能混为一谈。
- 运行质量：模型调用数、API 耗时、缓存命中、服务错误；服务中断停止，修复后续跑。

导出 episodes.csv、summary.csv、summary_by_fault.csv、attempts.csv、comparison.png、result.json 和图像。
论文按物体、故障及记忆阶段报告结果，不能只用所有条件混合的成功率。
统计分析应使用按场景种子配对的成功/失败数据；同一记忆链中的后续任务相互依赖，
不能把所有行作为完全独立样本。Wilson 区间仅作描述；显著性分析应考虑条件分层和记忆链依赖。

## 运行与边界

默认不打开窗口，仍使用 EGL 离屏渲染生成相机图像。无头不等于关闭视觉。
运行入口为项目根目录的 run_experiments.sh，使用现有 graspnet 环境。
每次新运行创建独立目录、独立数据库和配置清单；断点续跑保持配置、种子和经验状态。

```bash
conda activate graspnet
bash run_experiments.sh
bash run_experiments.sh --profile pilot
bash run_experiments.sh --profile thesis
# 先预览数量，或只检查依赖与离屏渲染；两者均不调用模型 API
bash run_experiments.sh --profile thesis --dry-run
bash run_experiments.sh --profile pilot --check-only
# 30 个任务的反思机制预实验：三组、一个物体、五种条件、每条件两次
bash run_experiments.sh --profile pilot --stages mechanism --methods retry reflection reflection_memory --sources RedBlock --faults none calibration collision slip placement --episodes 2
# 分阶段运行，每条命令会建立独立运行目录
bash run_experiments.sh --profile thesis --stages mechanism
bash run_experiments.sh --profile thesis --stages integrated verification_ablation
# 中断后指定原运行目录，配置、代码指纹与模型 ID 必须一致
bash run_experiments.sh --resume logs/reflection/experiments/原运行目录
```

可用 `--episodes 2` 覆盖选定阶段的每条件次数，`--seed 42` 设置起始种子，
`--scene-jitter 0.008` 设置各轴位置扰动范围（单位 m，上限 0.015）。
`--sources RedBlock GreenCylinder` 指定批量抓取物体，`--destination BlueBin` 指定共同的放置目标；
目标也可选 `RedBin`、`SortingTray`。批量模式当前只执行单物体抓取放置，不解析任意自然语言动作。
`--output 路径` 指定新的空目录；不传时自动创建时间戳目录。
运行入口会优先使用已激活的 graspnet 环境或本机现有环境；其他机器可设置 `GRASP_PYTHON`。

每个运行根目录的 `manifest.json` 保存矩阵、配置、代码/场景指纹、依赖版本、模型 ID 和预检结果，
不保存密钥。`REPORT.md` 显示完成进度和文件索引；`suite_episodes.csv` 汇总所有阶段。
每阶段导出 `summary_by_fault.csv` 与 `attempts.csv`，`comparison.png` 为整体描述图，
论文结论应以按条件分层的数据为主。

Ctrl+C 可中断；续跑跳过已有完整 `result.json`，恢复未完成任务开始前的经验快照。
模型服务异常不计入完成任务，保留 `service_error.json`，脚本停止并打印续跑命令；
恢复服务后使用同一目录续跑。模型输出结构非法则保留为算法失败，不替换成规则结果。
预检验证依赖、凭据是否存在、SAM 权重和 EGL 渲染，不发起网络探测，
因此 API 可用性由实际阶段调用检验。即使物理执行已经成功，遇到服务异常也会重跑该任务。

本实现仍使用仿真真值辅助错误检测，每次重试恢复初始场景，不是掉落后的真机原地恢复。
视觉验证消融仅研究验证策略，不能声称完成纯视觉真机安全检测。
故障强度当前固定，初始位置扰动较小；更广泛泛化需要单独设计强度、背景、遮挡与物体变化。
