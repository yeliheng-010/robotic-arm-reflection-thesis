# AI自主诊断：现有实现审查

2026-11-02（America/Los_Angeles）。用户接受将失败归因和修正选择交给AI。本审查只读取现有源码与记录，没有对961103追加根因标签或物理尝试。

## 结论

当前两场景执行线主要验证场景与执行器，不是AI自主诊断实验。另一条已有模型线研究有限菜单与补看选择，已有真实模型和物理实验，但其理想标签、按标签生成的候选和合成残差重采样限制了自主归因结论。应把工程正确性、策略决策和独立评估三层分开。

## 逐项证据

以下路径相对项目根目录；行号为本轮读取时位置。

| 发现 | 源码证据 | 对新实验的影响 |
|---|---|---|
| 当前入口明确记录model_calls=0 | `scene_pair_v2/pair_run.py:55`；`scene_diversity_v2/sd_physics.py:29,35` | 当前5/24与局部新增成功不能归功于AI诊断 |
| 模型只能返回action_id，不能提交可核查假设 | `active_observation_model_v2/am_policy.py:11,41` | 旧结果支持菜单选择结论，不直接测量自主归因 |
| 菜单按错误类型与阶段分支生成 | `bounded_reflection_v1/bounded/candidates.py:63`；`route_loop_v1/loopstudy/actions.py:36` | 即使去掉提示中的错误类型，菜单仍可能透露标签，需要一起改 |
| 投影保留理想错误类和阶段，部分测量含真值 | `controlled/feedback.py:16,32`；`noise_feedback_v1/projection.py` | “加了噪声”不代表其余字段已去除真值；两个噪声层不能混称 |
| quality目标字段的选择也依赖错误类 | `active_observation_pilot_v1/ap_policy.py:12` | 不能原样复用quality字段选择，否则泄漏仍从摘要进入 |
| OBSERVE重采的是原残差，未重渲染图像 | `active_observation_pilot_v1/ap_sensor.py:15,23,36` | 这是合成传感器协议，不等于重新看现场 |
| 单次尝试finally中关闭engine | `route_loop_v1/loopstudy/episode.py:13,23` | 真正补看须改变新版本的生命周期，保留失败时环境或可靠快照 |
| 动作/子阶段可从执行器获得 | `feedback_semantics_v2/semanticfix2/context.py:16` | 可保留“正在抬升”等命令上下文，不能混同根因答案 |
| goal_runtime会覆盖放置TCP、lift和预抓取姿态 | `scene_pair_route_v3/goal_runtime.py:24,29` | 必须对照requested/effective；不能让AI选了参数而实际被忽略 |
| 接触记录含物体真值位置、几何、接触力及对象身份 | `scene_pair_contact_diagnostic_v1/contact_data.py:41` | 不能整个contacts.jsonl直接交给主实验模型 |
| 采样时刻包括真值接触变化触发 | `scene_pair_contact_diagnostic_v1/contact_capture.py:34` | 仅删值仍可能通过事件标签/采样时刻泄漏；主观测应固定采样频率 |
| 当前基础模型服务按文本tokenizer输入 | `active_observation_model_v2/am_generator.py:18` | 文件路径或图片说明不等于模型已看图；多模态输入尚未接通 |

21份主要链路源码的哈希及两条账本核对见[OFFLINE_VERIFICATION.json](OFFLINE_VERIFICATION.json)。该记录证明本轮离线核对时文件未变，不是对全服务器当前运行状态的审计。

## 信息边界

| 信息 | 主实验可见性与前提 |
|---|---|
| 任务、自己发出的命令、实际尝试编号、剩余预算 | 可见；不附带案例seed、故障family或已知成功动作 |
| action、motion_segment、commanded_tcp_xyz | 可见，明确是命令记录，不能说是已实现动作或实测TCP |
| RGB/带噪深度、由这些数据估计的位置与可见性 | 感知接线、时间戳、标定和来源验证后可见；当前离线原型未附加 |
| 实际关节编码器及由机器人运动学计算的TCP | 新适配器接通后可见；不得用目标物体真值补齐缺测 |
| 接触对象身份、真值接触几何、原始物体位置/速度 | 留在评估侧；若研究理想触觉，单独标记为反馈条件，不包装成已实现传感器 |
| error_type、detector、诊断message、noise audit原值、根因解释 | 主实验输入排除；不能经菜单、quality或文件名迂回传入 |
| 最终inside_xy/inside_z/supported/settled、physical_success | 评估侧判分与控制器终止使用；不把其细节交给诊断策略 |
| 来源哈希、文件路径、种子、方法名、其他方法结果 | 仅审计侧保留；模型可见证据使用局部e1/e2编号 |

允许用共同的仿真辅助感知/规划组件作为底座，但应独立标记。去掉诊断标签不会自动把系统变成纯视觉系统；若感知仍用真值分割，应写“仿真辅助感知下的决策”，不能写“真实视觉独立归因”。

## 本轮实际交付

独立目录内新增输入白名单、能力菜单、输出校验及两种提示原型，未替换旧模块。隐藏标签、反馈文本、真值几何和种子的变更不影响actor输入。合法菜单按已登记能力、预算及感知候选数量决定，不按error_type分支；输出不合法就报错，不用规则代选。

18项本地测试通过。真实961103/961104第三次账本仅用于只读接口样例：预算0，默认能力未接通，仅STOP。样例包含命令记录，RGB/深度/时序观测均标记not_attached，不能拿它们测试完整掉落诊断能力。

该原型不调用模型，也不执行动作。即使输出提议校验通过，仍没有证明动作已生效、假设正确或物理恢复成功。新协议和后续门禁见[PROTOCOL.md](PROTOCOL.md)。
