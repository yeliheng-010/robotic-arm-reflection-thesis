# 当前两场景执行交接

更新时间：2026-11-02，Asia/Shanghai。当前入口为 `scene_pair_v2/pair_run.py`；新相机及后续三项局部修复已完成开发验证，尚无物理成功收益且仍有旧案例退步，未替换入口。

| 场景 | 行为 |
|---|---|
| baseline | 原布局、原物体朝向、原箱体配色、原相机，无新增噪声 |
| varied_noisy | 全局布局、物体朝向、箱体颜色、相机位置/朝向/FOV，同时加入3 mm深度高斯噪声和2%缺失 |

只有上述两种场景。版本目录是工程与实验留档，不是中间场景档位。

## 已完成与证据

1. `scene_pair_v2` 修复旧960102抬升掉落：前两次保持一致，第三次世界竖直候选成功；baseline仍首次成功。5754的12项测试通过，详见该目录README.md及anchor_verification.json。
2. `scene_pair_validation_v1` 冻结961101–961112的48条件：baseline24/24成功；增强5/24成功、14执行、10资格拒绝，共57次实际尝试。新增掉落补救在该批未触发，不证明泛化改善。5760审计、5761篡改检查通过。
3. `scene_pair_feasibility_v5` 保持布局/颜色/朝向/噪声和执行器，按当前任务选择首个可见、完整入画且深度一致的相机。22/24获得相机，24个增强条件完成记账；baseline复用24控制。50次新增尝试，成功5/24：新增3个成功，也有3个退步。5774全量审计及5775四项篡改拒绝通过，推广门禁false。

4. 按后续授权依次完成 `scene_pair_depth_v1`、`scene_pair_collision_v1`、`scene_pair_candidates_v1`。10＋3＋6项测试和三轮48条件审计通过；只新增3＋2＋6＝11次物理尝试，其他条件/前缀明确复用。深度缺失消除后变为放置失败；两个原无候选任务获得合法候选但抬升掉落；碰撞排序无新增成功。最终增强仍5/24，5788四项只读篡改拒绝通过，整体推广仍false。

最新完整报告：`scene_pair_candidates_v1/REPORT.md`；最终manifest SHA256为 `1a4e127f167c6f0255c6eadba798ce5c7e53fbc1e9ec995d7091ced7998c4307`。该目录CASE_DETAILS.json记录全部实际干预后果。

此前相机报告：`scene_pair_feasibility_v5/REPORT.md`。权威统计：`verification.json`；完整配对：`paired_ledger.json`；归因：`diagnosis.json`与`depth_diagnosis.json`。manifest SHA256为 `74726a77a70683d0f306bc9551e81d59dba224eb761c9602a562f67a63b68044`。

## 使用边界

服务器 `/home/yeliheng/grasp_server/scene_pair_v2`；加载该目录environment.sh，所有仿真通过Slurm。在该目录执行：

```bash
$SIM_PY pair_run.py --scene baseline --seed 960102 --output runs/original_960102
$SIM_PY pair_run.py --scene varied_noisy --seed 960102 --output runs/varied_noisy_960102
```

CLI支持960101–960112的已登记种子，输出目录必须不存在；默认RedBlock→BlueBin，也支持PurpleCapsule→RedBin。961101–961112通过独立冻结manifest执行，不能直接传给该CLI。已有耗时结果不需重新执行。新相机批量输出已存在，不要重新提交已完成的batch脚本。

## 明确未完成事项

增强场景整体仍不稳定。后续执行诊断已在`scene_pair_contact_diagnostic_v1`完成：6次精确回放、2次单因素对照，新增8次物理执行；5795审计通过。961103/961104证实机械臂碰目标箱被整箱ignore规则漏检；961108理想净空3.28 mm被实际跟踪偏差消耗；961104释放前0.1秒已失联但未达到0.2秒掉落门槛。961112单独减速和下移8 mm均无效，夹持根因仍未完全分离。详见该目录REPORT.md、diagnosis.json、final_audit.json。正式成功率仍5/24，诊断不扩大分母。

接触例外和释放前实际到位/持物检查已在`scene_pair_guard_v2`实施并定向验证：12次新增物理执行，最终10分支账本中7个旧成功逐值保持，两个碰箱失败提前中止，一次release-only诊断拒绝松爪。第一版额外限定源物体仅指垫接触导致1退步，范围修订恢复原有夹爪—源物体例外后消除；全部失败记录保留。5796的12测试、5800的4范围测试、5801最终审计通过。未重跑48条件、没有新增搬运成功、未替换当前入口；详见`scene_pair_guard_v2/REPORT.md`。

下一步将碰撞反馈接入预抓取/运输路径重规划，解决961103/961104绕箱路径；刀具动态净空、961112夹持几何、全量配对与未用种子验证仍待做。不能把提前中止描述为搬运已修复。

不降低噪声、不缩小布局变化、不按成功率挑相机或换种子。局部修复验证后须检查完整配对收益与退步，再登记未用种子；当前种子均已作为开发数据。所有冻结源码、manifest、成功/失败证据保留；v3/v4准备失败未做搬运，原因和诊断见最新REPORT。

没有新训练或语言模型对比。定位、分割、反馈仍有仿真真值辅助；容器自身旋转、质量/摩擦、光照未新增随机化。不宣称纯视觉、实机或盲测结果。完整图像/数组/轨迹在服务器，本地同步了关键文字证据及源码。
