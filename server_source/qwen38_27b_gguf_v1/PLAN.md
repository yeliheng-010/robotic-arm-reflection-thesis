# Qwen3.8-27B 四位量化部署

- 目标：固定UD-Q4_K_M权重，在两张V100上完成独立API部署与实际文本反思推理。
- 边界：新目录`/home/yeliheng/grasp_server/qwen38_27b_gguf_v1`，不修改已完成的Qwen3.5训练环境、adapter或封存test。暂不接管机械臂闭环端点，不宣称图像已验证。
- 数据来源：Unsloth量化自官方Qwen3.8-27B；ModelScope镜像仅作为传输来源，以固定HF revision对应SHA256验收。
- 资源：准备阶段CPU8/24G；推理阶段Slurm双GPU、单并发、4096上下文、FP16缓存、关闭thinking。
- 风险：V100算子兼容、加载临时显存、网络中断及生成不符合参数约束。保留失败日志，不对输出做规则回退或修补。
- 验证：脚本语法、编译退出码、权重哈希、实际双卡加载、health/models/chat API、普通中文回答、三个既有validation开发例的原始反思输出与合法性。开发例不等于全量评估。
- 流程：轻量计划与部署；采用verification-before-completion，实际构建和推理作为验收。
- 进度：准备3906已COMPLETED/0:0，哈希与构建通过；双GPU服务3907运行，health/models/chat API通过。
- 同256-token预算开发例合法2/3、参数匹配0/3；碰撞例单独增加预算到1024后正常结束并匹配规则。保留两个协议的独立证据，不合并结果。
- 实际解码约37 token/s，两卡占用7495/8565 MiB；模型部署成功，完整任务效果与视觉能力未验证。详见REPORT.md。

