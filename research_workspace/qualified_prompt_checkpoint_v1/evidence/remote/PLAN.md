# 978505末尾拒绝动作核对：一次模型验证

2026-11-18用户采纳上一阶段建议，授权新实验最多1次模型生成；规划、物理、训练、相机搜索均为0。不得重提旧两决策或旧物理脚本，不删除claim，不修改旧冻结源码或结果。

目标：在同一已合格RGB、完整公开观测、系统指令、动作白名单、历史与解码参数下，查看模型是否遵守非重复约束。采用已保存B草案的末尾decision_checkpoint；C阶段文本清理不启用。实际请求将planning预算由1改为0，decisions仍1，observations仍0，以如实描述本轮权限。因此与历史基线相比有checkpoint和预算字段两处变化；不声称严格单变量因果结论。

1. 先在Slurm验证请求边界、严格输出处理及排他预算锁：预期失败检查后实现并通过测试。
2. 新目录登记一次预算，冻结旧来源、旧结果与claim、新脚本、原RGB、B草案，以及生成器/运行时的项目来源和模型processor/tokenizer配置。记录依赖版本。
3. 生成前排他消费唯一claim；工程异常、超长输入、非法输出、重复、STOP均停止且不补抽。保存实际输入token/attention与全部输入张量、模板、生成配置和生成开始标记，禁止私有诊断进入提示词。
4. 仅生成一次并严格解析，分类invalid/repeated_rejected_action/model_stopped/novel_action_unchecked。不生成proposal，不做静态预检或物理执行；新颖动作不等于安全。
5. 在独立Slurm进程重新核验来源、重建请求、解析原始响应、复核输入张量、模板和预算。审计可重新编码但不得调用generate；不重跑旧基线。
6. 结束后哈希同步全部新证据，保存报告、更新CURRENT_STATUS。失败如实记录，不以单案例证明普遍反馈能力或成功率提升。

验收：模型生成≤1，规划/物理/训练=0；无旧证据变更；输入/输出/预算/源码可复核；结果无论新动作、STOP或重复都按协议收尾。技能流程：brainstorming、writing-plans轻量规划，test-driven-development、verification-before-completion；串行执行，不新增依赖、根配置、Git操作或子代理。
