# Qwen3.8-27B 四位量化部署结果

已完成独立双V100文本推理部署，权重哈希、编译、健康检查、模型列表和真实聊天请求均通过。服务作业3907当前运行；这不是27B微调，也没有替换已有Qwen3.5-4B adapter或机械臂闭环端点。

## 服务与资源

| 项目 | 实测或固定配置 |
|---|---|
| 模型 | Qwen3.8-27B，Unsloth UD-Q4_K_M GGUF，混合精度四位量化 |
| 文件大小 | 16,464,440,224 bytes，约15.33 GiB |
| 引擎 | llama.cpp，固定源码revision见manifest.json，CUDA12.9/sm_70本机构建 |
| 模型别名 | `qwen3.8-27b-q4` |
| 服务器内部API地址 | `http://127.0.0.1:38271/v1` |
| GPU | 0、1；GPU2、3收尾检查时空闲 |
| 显存占用 | 7495 / 8565 MiB，约7.32 / 8.36 GiB |
| 上下文与并发 | 4096 tokens、单并发，关闭thinking、FP16 KV缓存 |
| 解码速度 | 本次短请求约36.8–37.4 token/s，不是长上下文或并发吞吐基准 |
| 准备作业 | 3906 COMPLETED/0:0，21分27秒，下载与编译并行 |
| 服务作业 | 3907 RUNNING，单次Slurm时限4小时 |

权重从ModelScope公共镜像获取，最终SHA256与固定Hugging Face revision一致：`322e194ff79741c7baa497c240f677f54b201b0efab44ca8e50f122b39123482`。

构建使用官方源码压缩包，程序版本输出中的commit为unknown；可追溯身份以manifest中的源码revision、下载地址、source-archive.sha256及engine.sha256为准。加载器忽略了可选MTP层张量，本次未启用MTP。

当前端点只供服务器内部程序或Jupyter终端访问。已检查Jupyter `/proxy/38271/health` 返回404，未宣称有外部浏览器入口。视觉投影文件未下载，因此未验证图像输入。

## 实际输出与边界

普通中文请求成功，29个输出token，端到端约1.06秒。固定使用现有validation的前三个类别开发例，未读取封存test，未执行物理仿真。

| 开发例 | 256-token预算结果 | 与规则参数匹配 |
|---|---|---|
| calibration | 合法JSON，选择candidate_index=1 | 不匹配；规则标签修正grasp_offset |
| collision | cause解释过长，finish_reason=length，JSON被截断 | 不匹配 |
| placement | 合法JSON，place_offset=[-0.16,0,0] | 不匹配；所需X偏移为正值 |

同预算结果：2/3通过现有参数合法性检查，0/3参数完全匹配。这只是3个开发例，不是全量评估，也不能等同于物理成功/失败率。

针对碰撞例，仅将max_tokens提高到1024，保持提示、greedy和其余配置不变。模型生成416个token后正常结束，JSON合法，`lift_height=0.45`与规则标签完全匹配，端到端约11.82秒，解码约37.29 token/s。该请求复用了提示缓存；这是独立输出预算诊断，不能并入原256-token对照宣称同预算提升。

建议先将该端点用于候选模型比较或教师试采。机械臂主线继续保留已有微调模型，待27B完成提示/输出预算验证与同预算闭环对照后再决定是否替换。

## 调用与重新启动

在服务器Jupyter终端执行：

```bash
curl http://127.0.0.1:38271/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3.8-27b-q4","messages":[{"role":"user","content":"用一句话说明如何检查机械臂抓取偏移。"}],"temperature":0,"max_tokens":1024,"chat_template_kwargs":{"enable_thinking":false}}'
```

1024是后续试调用的输出预算建议；同时确保输入与输出总长度不超过配置的4096上下文。它不会自动解决参数方向或选择错误。

服务因4小时时限结束后，可重新提交已有服务脚本，无须重新下载或编译：

```bash
sbatch /home/yeliheng/grasp_server/qwen38_27b_gguf_v1/serve.sbatch
```

新作业会重新做健康和三个开发例检查，各作业保留独立`smoke-<jobid>.json`。已运行时不要重复提交；脚本检测端口占用并退出。原始开发例检查仍使用256-token固定预算，便于复查。

## 证据

- 固定配置：[manifest.json](manifest.json)
- 原始冒烟请求、回答、计时和合法性：[smoke-3907.json](smoke-3907.json)
- 1024-token单例诊断：[collision_budget1024.json](collision_budget1024.json)
- 作业快照：[slurm_status.txt](slurm_status.txt)
- 服务器目录：`/home/yeliheng/grasp_server/qwen38_27b_gguf_v1`
- 使用技能：verification-before-completion；截断问题按systematic-debugging追踪finish_reason后做单变量诊断。

