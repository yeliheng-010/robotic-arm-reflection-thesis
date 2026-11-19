# VLM_Grasp_Interactive
参考文章进行环境配置
https://blog.csdn.net/agentssl/article/details/148089323

1.配置环境
conda create -n vlm_graspnet python=3.10
conda activate  vlm_graspnet

创建主文件夹
VLM_Grasp_Interactive

主文件夹中移植下面项目的manipulator_grasp操作包（进去找这个文件夹）
git clone https://gitee.com/chaomingsanhua/manipulator_grasp.git

主文件夹中下载graspnet-baseline项目
git clone https://github.com/graspnet/graspnet-baseline.git

打开graspnet-baseline，修改其中的requirements.txt
cd graspnet-baseline
sudo gedit requirements.txt 

保存后执行安装指令
pip install -r requirements.txt

安装torch等所需的环境包
pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==0.12.1 --extra-index-url https://download.pytorch.org/whl/cu113
pip install spatialmath-python==1.1.14
pip install roboticstoolbox-python==1.1.1
pip install modern-robotics==1.1.1
pip install mujoco==3.3.1

编译并安装PointNet++自定义算子
（PointNet++是处理3D点云的经典神经网络，需要自定义CUDA算子实现高效采样和特征聚合/VoteNet是基于PointNet++的3D目标检测框架）
cd pointnet2
python setup.py install
cd ../

编译并安装基于PyTorch CUDA实现的k-最近邻（k-NN）算子：
- k-NN算子：用于快速计算数据点之间最近邻关系的算法模块
- CUDA加速：利用NVIDIA显卡进行并行计算加速
- PyTorch扩展：为深度学习框架添加自定义C++/CUDA操作
cd knn
python setup.py install
cd ../

安装graspnetAPI工具包
git clone https://github.com/graspnet/graspnetAPI.git
cd graspnetAPI

修改setup.py，将sklearn替换为scikit-learn
sudo gedit setup.py

修改后开始安装
pip install .
cd ../

下载GraspNet-baseline的权重(训练好的)

在VLM_Grasp_Interactive文件夹新建logs/log_rs文件夹，将下载好的权重checkpoint-rs.tar放进log_rs


继续完善环境（可以运行代码，缺啥pip啥，版本兼容情况做对应修改）【每个人有自己的玄学体质，后续考虑docker打包】
pip install opencv-python
pip install --force-reinstall "numpy==1.26.4
pip install ultralytics==8.3.98
pip install "opencv-python==4.5.5.64" --force-reinstall
pip install openai-whisper
pip install soundfile
pip install sounddevice
pip install pydub
pip install openai
#进入 graspnetAPI 目录并安装 pip install -e .
pip install --upgrade transforms3d

## 优化版抓取后端

当前版本支持三种后端，通过环境变量 `GRASP_BACKEND` 选择：

```bash
# 默认：GraspNet 经过目标约束与场景碰撞筛选，失败时回退几何抓取
python main_vlm.py

# 简单俯视桌面任务：不加载 GraspNet，速度快且结果可解释
GRASP_BACKEND=geometric python main_vlm.py

# 只使用增强后的 GraspNet，不允许回退
GRASP_BACKEND=graspnet python main_vlm.py
```

运行离线回归测试：

```bash
python -m unittest discover -s tests -v
```

详细设计、验证结果和后续模型升级路线见
[`docs/GRASP_OPTIMIZATION.md`](docs/GRASP_OPTIMIZATION.md)。

## 杂乱桌面语义分拣场景

默认场景现包含蓝/红两个开放投放箱、黄色浅托盘、安全隔板，以及红色方块、绿色圆柱、紫色胶囊和橙色小球。新增道具独立定义在
`manipulator_grasp/assets/scenes/sorting_props.xml`，可直接调整位置、尺寸或颜色。

建议按下面顺序逐步增加实验难度：

1. `把红色方块放到黄色托盘中`：基础定位、抓取和精确放置。
2. `把香蕉放进蓝色箱子`：细长物体抓取与容器投放。
3. `把紫色胶囊放进红色箱子`：短轴抓取、长距离搬运和遮挡。
4. `绕过隔板，把绿色圆柱放进蓝色箱子`：抬升越障与完整场景碰撞测试。
5. `把所有红色物体放进红色箱子`：开放词汇、多实例和连续任务规划。

放入箱子时应定位开口中心并使用约 `0.12 m` 的释放高度；放到浅托盘时建议使用约 `0.08 m`。

## Isaac Sim 5.1：原生家庭具身智能演示（推荐）

`isaac_embodied_demo` 是当前主演示。画面、物理世界、状态日志和按钮都在
**Isaac Sim 原生窗口**中，不使用浏览器动画。默认任务完整复现 MuJoCo 家庭任务：移动
Franka 依次把水杯和药盒送到照护区，把玩具放进有底板和围壁的收纳箱，并保持水杯直立。

场景包含客厅源桌、照护台、收纳箱、缓冲台、中央隔断和两条可行通道。餐桌、沙发、冰箱、
植物、餐盘与 YCB 水杯采用 NVIDIA 官方资产；室内地板和墙体在本地组合，不再嵌套带草地、
道路和重复家具的整体外景。家具位置经过尺寸审计，地面、墙、台面、家具、餐盘、箱体和任务
物品均有明确碰撞体。

这不是“物体跟随动画”：任务物品始终是动态刚体。控制器只有在 PhysX 同时报告左右手指
接触后才创建保留相对位姿的 `UsdPhysics.FixedJoint`；移动底盘通过 A* 路径连续平移，把所持
物与目标对齐；释放时删除关节，让物体在重力下落到支撑面。每个子任务都必须通过位置、姿态、
线/角速度、支撑接触、夹爪脱离和关节删除验证。控制器不会在运输中调用任务物品的
`set_world_pose()`，也不会把任务物品设成 kinematic。物理设置为 120 Hz PhysX、TGS、CCD、
高求解迭代和高摩擦材质。

本机已经安装 Isaac Sim 5.1 Python 环境。用户接受 NVIDIA Omniverse EULA 后，启动原生
GUI：

```bash
cd /home/yeliheng/桌面/VLM_Grasp_Interactive
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo
```

如果希望加载完成后立即自动演示：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo --auto-start
```

现场展示建议使用“自适应完整演示”。它会执行全部三个家庭子目标，并在水杯运输途中生成一个
有碰撞体的实体障碍；机器人会停车、更新地图，再将视口中的青色 A* 路径改为橙色重规划路径：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo --showcase
```

首次运行会从 NVIDIA 官方 Isaac 5.1 资产服务器下载并缓存住宅资产；后续运行复用缓存。原生
`omni.ui` 面板提供：

- `Run Full Mission`：执行水杯、药盒、玩具的完整多区域任务；
- `Adaptive Showcase`：一键执行完整任务，并自动展示实体障碍与在线换路；
- `Move Current Object`：施加外力，触发重新定位和计划修订；
- `Inject Drop`：删除当前物理抓取约束，观察真实下落和恢复；
- `Block Lower Route`：激活实体障碍并从默认下通道改走上通道；
- `Occupy Care Slot`：将当前照护物品改送缓冲台并记录占用事件；
- `Reset Scene`：重置 USD/PhysX 状态，但保留 SQLite 长期记忆。

Isaac Sim 5.1 在当前系统中无法稳定加载 CJK 字体，因此面板使用英文以避免现场演示出现乱码；
本节提供中文按钮含义。

无窗口物理回归（不会启动网页）：

```bash
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo \
  --headless --auto-start --max-steps 20000
```

异常路径也可以确定性注入，便于录制和持续集成：

```bash
# 阻塞默认下通道，A* 改走上通道
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo \
  --headless --auto-start --inject-block-step 1000 --max-steps 22000

# 计划执行中对当前物品施加外力
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo \
  --headless --auto-start --inject-move-step 250 --max-steps 22000

# 已建立物理抓取后删除约束，等待真实掉落后重新定位和抓取
OMNI_KIT_ACCEPT_EULA=YES .venv-isaacsim/bin/python -m isaac_embodied_demo \
  --headless --auto-start --inject-drop-step 1000 --max-steps 22000
```

可用 `--asset-root` 切换到本地资产镜像，用 `--save-stage path.usd` 导出组合场景。认知状态、
场景构建、机器人控制和 UI 分别位于 `state.py`、`scene.py`、`controller.py`、`ui.py`；后续增加
机械臂、移动底盘或其他具身工具时，可以新增设备适配器和任务控制器，而不必重写住宅场景与
长期记忆层。

已知环境边界：Ubuntu 25.04 不在 Isaac Sim 5.1 官方支持矩阵内，但当前 RTX 5070/驱动
570.195.03 已实际通过 RTX 与 PhysX 回归；Isaac 环境内的 PyTorch 2.7 不包含 `sm_120`，
后续神经推理应放到使用新版 PyTorch 的独立服务，仿真控制进程不受影响。

## Future AI Emulator：MuJoCo 原生具身智能演示（旧版）

`future_embodied_demo` 是一个完全离线、不会调用大模型 API 的可运行概念原型。它用确定性的目标规划、MuJoCo 真值世界模型、动作后验证和 SQLite 长期记忆，模拟“毫秒推理、零幻觉、无限记忆”成立时的具身系统外部行为。界面会明确标注这是未来能力模拟器，不把受控语言解析包装成通用智能。

默认演示是一台安装 UR5e 的移动操作机器人，在客厅桌、照护区和收纳区之间完成：

```text
把客厅桌上的水杯和药盒送到照护区，
把玩具放进收纳箱，并保持水杯直立
```

默认启动的是 **MuJoCo 原生三维窗口**，而不是网页动画：

```bash
conda activate graspnet
python -m future_embodied_demo
```

主场景、机械臂与移动底盘运动、物理结果、AI 计划和事件日志都直接显示在 MuJoCo 窗口中。鼠标可旋转、平移和缩放摄像机，键盘控制如下：

- `Enter`：启动默认家庭整理任务。
- `1`：阻塞上通道，观察安全停车和换路。
- `2`：移动水杯，观察重定位和计划修订。
- `3`：在夹持期间注入脱落。
- `4`：占用照护区，观察暂存、清障和恢复原目标。
- `5`：移除动态通道障碍。
- `R`：不关闭 MuJoCo 窗口地重置场景，同时保留 SQLite 长期记忆。
- `S`：在当前技能边界安全停止。
- `H`：显示或隐藏窗口内 HUD。

如果只需要查看 HTTP 状态、调试接口或录制帧，可显式启动可选网页调试器：

```bash
python -m future_embodied_demo --web
```

然后访问 `http://127.0.0.1:8765`。网页不再是主演示界面。在任一界面注入通道阻塞、物体移动、夹持脱落或目标占用后，系统都会在技能边界比较预期与 MuJoCo 真实状态，解释异常、写入经验并生成修订计划。

无需网页的快速验证：

```bash
python -m future_embodied_demo --no-realtime --run-command \
  "把水杯送到照护区并保持直立"
```

运行新增回归测试：

```bash
python -m unittest discover -s tests -p 'test_future_embodied*.py' -v
```

架构通过 `CapabilitySpec` 注册身体能力，通过 `SkillRequest` / `SkillResult` 隔离认知层和设备层。后续可以增加机械臂、移动底盘、摄像头或其他具身工具，而无需修改目标、世界模型和记忆协议。
# 机械臂错误反馈与智能反思

接续 Claude 的研究生论文开发会话。新增 `reflection` 提供四阶段检测、规则/LLM 反思、
SQLite 经验记忆、VLM 视觉验证和真实 MuJoCo 抓取闭环；`experiments.run_benchmark` 提供四组对比。

```bash
conda activate graspnet
python -m reflection --fault collision
python -m reflection --instruction "把绿色圆柱放进蓝色箱子" --fault none --viewer
python -m reflection --interactive --task-parser llm --reflector llm --fault none --viewer
bash run_experiments.sh
bash run_experiments.sh --profile thesis --dry-run
```

默认是离线规则对照，模型模式、实验协议和仿真真值边界详见 [reflection/README.md](reflection/README.md)。
交互模式先显示仿真环境，再等待自然语言输入，连续任务共用窗口。
论文实验设计与无头批量运行、断点续跑见 [experiments/PROTOCOL.md](experiments/PROTOCOL.md)。
