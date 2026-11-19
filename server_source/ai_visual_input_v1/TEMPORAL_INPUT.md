# 生成前的图像输入修订

5914准备完成，但源物体mask像素不足，未生成裁剪，只有失败后的完整相机帧。此时尚未加载模型或调用生成。为让模型看到真实动作前后变化，改用同一已审计尝试内保存的before.png及默认暂停后的RGB，两张都已存在，不渲染新帧、不增加旧轨迹观测预算。

已只读核对冻结reflection/engine.py：before.png直接保存动作前env.render的RGB，没有原因标签或标注。默认暂停帧仍来自原Sampler。两模式共享这两张图及同一执行事实，图像顺序明确为before、after。

旧input/manifest/准备日志保留；执行使用temporal_v2/input.json及独立manifest。总调用预算仍为2，旧输入生成0次。该修订不提供根因或正确动作，仍不证明诊断正确。
