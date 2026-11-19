# 模型及训练路线预检

2026-10-26实时读取服务器文件、GGUF元数据、已安装Python包和Slurm状态。用户已明确同意4B学生微调，Flash保留教师。

Flash本地目录：`/home/models/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/IQ3_S`。两分片大小54,817,524,224和28,800,138,432字节，合计约77.88GiB；GGUFReader统计张量元素125,743,653,760和51,200,245,760，总约176.94B。张量元素计数不是对官方发布模型参数量的独立认证。

内部元数据：general.architecture=qwen4exp，general.name=Qwen3.8-Flash-Next GSQ-RCO，48层，512专家，每token选择10专家，context_length=262144；repo_url指向ISTA-DASLab同名GGUF仓库。这是权重内部声明，未单靠服务别名验证官方基础checkpoint身份。

已检索/home/models、用户qwen35目录及用户HF缓存指定深度，找到Flash GGUF，未找到对应HF可训练checkpoint。训练环境torch2.6.0+cu124、transformers5.20.1、peft0.21.2、bitsandbytes0.49.2；CONFIG_MAPPING_NAMES不含qwen4exp，含qwen3_5。仅上述现有工具链不能直接执行该Flash GGUF的QLoRA；没有宣称所有CPU卸载/定制训练路线理论上都不可行。

四卡均Tesla V100-SXM2-16GB，检查时显存1/1/2/5MiB，Slurm队列为空。主机250GiB内存，约236GiB可用，/home剩余约143GiB。Flash仅现有量化文件已经大于四卡合计64GiB，因此不能把它的CPU/GPU混合推理成功当作四卡训练可行性证据。

实际学生：`/home/yeliheng/grasp_server/qwen35/models/Qwen3.5-4B`，config.architectures=Qwen3_5ForConditionalGeneration，model_type=qwen3_5；本地完整safetensors和tokenizer均存在，LICENSE文件存在。模型、tokenizer、配置和许可文件的实际SHA256统一保存在manifest.json。沿用已验证4B NF4/FP16与FP32 delta-rule设置，全注意力使用SDPA且关闭V100不支持的Flash内核，微批1。

真实tokenizer预检：train159，2430—9439 tokens，中位4154；dev49，2430—7562，中位4160；legacy_dev29，5877—6800，中位5899。监督后缀17—22 tokens。无截断，全部assistant-only mask及模板前缀验证通过。所有指标限定该学生tokenizer，不能拿去声称Flash输入token数。
