# 当前场景执行交接

当前入口：`scene_pair_v1/pair_run.py`。用户要求只保留两种配置，已落实：

| 配置 | 行为 |
|---|---|
| baseline | 原布局、原物体朝向、原箱体颜色、原相机，无新增噪声 |
| varied_noisy | 全局布局＋物体朝向＋箱体颜色＋相机位置/朝向/FOV，同时加入3 mm深度高斯噪声与2%缺失 |

当前没有中间组合开关。种子只改变增强场景的具体实例，不增加配置档位。

## 使用与验证

服务器目录：`/home/yeliheng/grasp_server/scene_pair_v1`；加载同目录environment.sh，在Slurm环境中执行：

```bash
$SIM_PY pair_run.py --scene baseline --seed 960102 --output runs/original_960102
$SIM_PY pair_run.py --scene varied_noisy --seed 960102 --output runs/varied_noisy_960102
```

输出目录必须不存在。当前开发种子960101–960112；默认RedBlock→BlueBin，也支持PurpleCapsule→RedBin。完整说明见`scene_pair_v1/README.md`。

- Slurm 5753：COMPLETED/0:0，1分45秒，6项测试通过。
- 两场景真实渲染、标定、可见性及深度注入审计通过。
- 原配置深度误差/缺失均0，1次搬运成功。
- 增强配置实测深度RMSE 2.993 mm、缺失2.011%；3次搬运均object_dropped。
- 噪声随外层尝试编号变化，所有4次实际尝试均核对传感器记录；场景初态一致。
- 8个运行文件与本地哈希一致；旧冻结源码保持不变。
- 最终检查用户队列为空，四GPU利用率0%，显存1/2/4/5 MiB。

这是单个已使用开发种子的接入验证，不能作为总体成功率或模型效果对照。没有重新运行144条件实验，没有训练或封存测试。

## 范围与留档

全部变化指本轮已有的布局、物体朝向、箱体配色、相机变化。容器自身旋转、质量/摩擦和光照仍未扩展。定位和分割仍有仿真真值辅助；噪声只进入传感输入，不污染物理成功判据。

旧`scene_diversity_v2`作为冻结实现依赖和历史实验保留，其分组不再作为当前使用入口。历史144条件结果详见该目录REPORT.md，不改写为本轮带噪结果。

当前证据：`scene_pair_v1/verify-5753.log`、`scene_pair_v1/smoke/*/result.json`、`scene_pair_v1/smoke/*/preview/sensor_trace.json`。

下一步如继续优化，仅围绕上述两种配置修复增强场景的抓取稳定性，不恢复中间组合。
