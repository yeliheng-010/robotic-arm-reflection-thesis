# 机械臂错误反馈与智能反思系统：接管记录

更新日期：2026-10-19。用于后续继续开发时恢复项目状态。

## 会话与代码基线

- 已读 Claude 会话至末尾：`/home/yeliheng/.claude/projects/-home-yeliheng---/2392efee-a977-477a-b5fe-accafd4524a8.jsonl`。
- 会话最后一条实际对话时间为 2026-10-08T11:11:33.640Z；文件修改日期不代表新增对话日期。
- 项目：`/home/yeliheng/桌面/VLM_Grasp_Interactive`。
- 分支：`feat/error-feedback-reflection`；接管时 HEAD：`3df8ed6`。
- Python：`/home/yeliheng/miniconda3/envs/graspnet/bin/python`。
- 接管前已有两个 tracked `.pyc` 文件修改，保留原样。后续新增 `training/qlora`，未修改机械臂执行逻辑。
- 会话和 `.env` 内的凭据不复制到本记录。服务器已完成单卡 7B QLoRA 短训练，尚未部署推理服务。

## 已核对的新增功能

1. `reflection/llm.py` 已使用流式响应收集内容，处理空响应、额度耗尽与突发限流。Claude 遇到的 HTTP 200 空内容问题不能一概归因为额度耗尽。本轮仅审阅代码，未请求在线服务。
2. `reflection/reflector.py` 的 `reflect-v2` 提示词去掉错误类型到修正值的对应规则，只提供参数范围、含义和证据解释。
3. `reflection/engine.py` 的 `plan-ground-v3` 让 VLM 根据指令和图像选择物体、定位；不提供正确源物体名称和答案动作实例。仍约束五步动作协议。选错对象由计划验证报告。
4. 桌面 `启动机械臂.sh` 可先显示窗口再在终端输入指令，也可直接传入一条中文指令；默认模型为 122B，使用 SAM、LLM 任务解析、LLM 反思和经验记忆。
5. 上述桌面入口**默认感知是 simulation**，未启用 `--perception vlm`；视觉验收默认关闭。语言理解、图像规划、分割、反思和验收是分别配置的功能。
6. `demo_meeting.sh` 已有正常任务、碰撞反思、记忆复用、放置修正和交互演示入口。演示允许响应缓存，与正式实验配置不同。
7. 黄色托盘的颜色标签已修复。普通自然语言入口支持四种源物体；suite 包装器目前只允许红色方块、绿色圆柱两种源物体。

## 数据来源与边界

| 数据 | 位置（项目内相对路径） | 已核对的结果与用途 |
| --- | --- | --- |
| 原 30 项实验 | `logs/reflection/experiments/pilot_20261007_171048_bea839` | 27B，三个方法×一个物体×五种条件×两个任务；旧提示词、仿真感知机制实验，不能当作新提示词下的完整视觉结果 |
| 122B 完整链路 10 项 | `logs/reflection/experiments/pilot10_q122b` | manifest 确认 122B；VLM 规划定位、SAM、几何抓取、LLM 反思、VLM 验收；10 个唯一任务及结果文件齐全；retry 3/5、reflection 2/5，记录 51 次模型请求 |
| 早期完整链路未完成运行 | `logs/reflection/experiments/pilot10_integrated`、`pilot10_integrated_v2` | 留有服务异常和不完整输出，不与完成的 122B 数据混用 |
| 去先验提示单次复测 | `reflection/VALIDATION.md` 末尾 | Claude 记录的 397B 单次验证，不是多次统计实验；本轮未在线重跑 |
| 组会导出资料 | 桌面 `组会实验数据/` | 来自原 27B 的 30 项实验，包含原始 CSV、四张数据表和图；不是 122B 的 10 项结果 |

122B 数据每个方法、每种故障仅一个任务，且没有记忆组，不足以证明方法优劣或记忆收益。该运行保存的代码提交为 `e281310`，不是当前 HEAD。批量任务先用规则解析已知对象指令，VLM 再执行图像规划定位，并非测试自由自然语言解析能力。

各运行的 `suite_episodes.csv` 是任务汇总，阶段目录下的 `attempts.csv` 是逐次尝试；`result.json` 保留错误、修正、参数、物理验收和视觉验收，`attempt_N/` 保存图像与计划。原有 CSV 字段说明位于桌面 `机械臂30任务实验运行与CSV字段说明.md`，其中旧模型示例需结合当前配置理解。

## 待办及建议顺序

### 1. 优先解决反思后的运动失败

- 当前 IK 失败只报告通用消息及抓取坐标，不能区分接近、抬升、搬运、放置等段，也未给出失败目标位姿。
- 122B 碰撞任务的证据：第 1 次撞到隔板，模型将 `lift_height` 提高到 0.48；第 2 次出现 IK 失败，最终未完成。
- 下一步补充失败运动段、目标位姿、当前参数和求解信息；对候选修正检查可达性，再决定执行或向模型反馈。不能仅依靠参数数值在合法范围内。

### 2. 校准实验故障与验收

- 检查 placement 注入在仿真感知与 VLM 定位路径下是否形成可比偏差。122B 两个 placement 任务均首次成功，尚不能据此声称完成了放置故障恢复。
- Claude 曾记录机械臂遮挡导致视觉验收假阴性；本轮核对的 122B 汇总中 visual veto 为 0，因此该运行不能量化此问题。需要单独复现并评估拍摄时机、视角及不确定输出处理。
- 固定代码、模型、提示版本、视觉配置和故障口径后，再扩大样本。336 项 pilot、1120 项 thesis 尚未整体完成。

### 3. 完善入口与模型服务适配

- 桌面脚本只对 `--fault` 专门解析取值，其余 `--*` 被当作单独开关；例如 `--perception vlm` 的 `vlm` 会被误当成指令。带值选项目前应直接调用 Python CLI。
- 桌面和组会脚本固定本地代理地址。后续可改善代理与参数透传，避免切换环境时手动改脚本。
- 接入自建模型前核对预检与鉴权：`LLMClient` 支持配置兼容 API 的 base URL，但目前要求非空 key；其他入口的限制仍需逐项确认。不要直接假定所有路径都已兼容本地服务。
- 远程服务器已于 10/19 再次登录，随后在 `~/grasp_qlora/env` 安装独立 Python 3.11/CUDA 训练依赖。Slurm 作业 3608 在单张 V100 上完成 Qwen2.5-7B-Instruct 的 NF4/FP16 QLoRA 8 步训练与 adapter 保存重载；完成后 GPU 2/3 空闲，GPU 0/1 服务未修改。当前只有一条合格修正样本，仅证明流程可用。详见 [实测记录](../training/qlora/VALIDATION.md) 和 [启动说明](../training/qlora/README.md)。尚未接入推理服务，未验证多卡或独立任务效果。

## 当前运行入口

先看环境，再输入自然语言：

```bash
bash ~/桌面/启动机械臂.sh
# 窗口出现后，在启动它的终端输入：把绿色圆柱放进红色箱子
```

直接执行一条指令：

```bash
bash ~/桌面/启动机械臂.sh "把红色方块放进蓝色箱子"
```

显式开启完整视觉链路（会调用在线模型；在已配置凭据和网络的终端运行）：

```bash
cd ~/桌面/VLM_Grasp_Interactive
REFLECTION_MODEL_ID=Qwen/Qwen3.5-122B-A10B \
 /home/yeliheng/miniconda3/envs/graspnet/bin/python -m reflection \
 --viewer --interactive --fault none --method reflection_memory \
 --task-parser llm --perception vlm --segmentation sam --reflector llm \
 --output "logs/reflection/interactive_$(date +%Y%m%d_%H%M%S)"
```

需要视觉验收时加 `--visual-verify`，并记录上述遮挡问题。

无头批量入口（默认 smoke 是 24 项离线规则检查）：

```bash
cd ~/桌面/VLM_Grasp_Interactive
bash run_experiments.sh
# 仅预览：红方块到红箱，两个方法×五条件×一次，共 10 项
REFLECTION_MODEL_ID=Qwen/Qwen3.5-122B-A10B bash run_experiments.sh \
 --profile pilot --stages integrated --methods retry reflection \
 --sources RedBlock --destination RedBin \
 --faults grounding calibration collision slip placement --episodes 1 --dry-run
```

上述命令去掉 `--dry-run` 才实际执行。`--sources` 指定抓取物，`--destination` 指定放置目标；无头仍运行机械臂物理仿真并保存相机图像。suite 当前支持的源物体为 `RedBlock GreenCylinder`，目标为 `BlueBin RedBin SortingTray`。

正式实验禁用响应缓存。新运行使用新目录；只有代码指纹和配置一致才能 `bash run_experiments.sh --resume 原运行目录`，不要修改旧 manifest 绕过检查。完整方案见 [PROTOCOL.md](../experiments/PROTOCOL.md)。

## 本次接管验证

- 反思、语言与实验管理回归：24 项通过（2026-10-19）。测试使用离线替身，不证明今日在线模型服务可用。
- `bash -n`：`demo_meeting.sh`、`run_experiments.sh`、桌面 `启动机械臂.sh` 均通过；仅验证 shell 语法。
- `bash run_experiments.sh --profile thesis --dry-run`：560 + 280 + 280 = 1120，未执行任务。
- 最初接管检查未调用模型 API、未重跑 GUI 或大批量实验；后续服务器短训练的范围与证据见上方实测记录。

回归命令：

```bash
cd ~/桌面/VLM_Grasp_Interactive
env PYTHONDONTWRITEBYTECODE=1 MUJOCO_GL=egl \
 MPLCONFIGDIR=/tmp/grasp-reflection-matplotlib PYTHONPATH=tests:. \
 /home/yeliheng/miniconda3/envs/graspnet/bin/python \
 -m unittest discover -s tests -p 'test_reflection*.py'
```


## 2026-10-19 服务器迁移补充

主要工作环境已迁移到 `/home/yeliheng/VLM_Grasp_Interactive`；服务器家目录的
`机械臂项目任务说明.md` 与 `GPT对话接续摘要.md` 是最新接续入口（本地副本在
`training/server/`）。无头采集、训练、评估在服务器，模型通过独立评估后再回迁本地 GUI。

部署已校验代码与资产，服务器 EGL 渲染及物理碰撞恢复验收通过（Slurm3612）。
首批60任务采集为3613，冻结Qwen2.5-7B教师为3609；数量以实时status.json为准。
Qwen3.5-4B初次训练检查3611在梯度检查失败，尚未验证训练成功；稳定性重试
使用隔离代码副本排在采集后，结果见grasp_server/jobs.json与qwen35/runs。
当前只使用物理GPU2/3，不停止GPU0/1服务。四卡安排需明天释放后重新核对。
