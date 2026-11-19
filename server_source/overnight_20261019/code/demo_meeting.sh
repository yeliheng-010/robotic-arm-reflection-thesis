#!/usr/bin/env bash
# 组会演示一键脚本。用法：
#   bash demo_meeting.sh 1    # 环节1：正常抓取（对照）
#   bash demo_meeting.sh 2    # 环节2：隔板碰撞 → 检测 → 大模型反思 → 修正成功
#   bash demo_meeting.sh 3    # 环节3：同一场景再来一次 → 命中经验记忆，一次成功
#   bash demo_meeting.sh 4    # 环节4：放置偏差 → 根据残差补偿
#   bash demo_meeting.sh 5    # 环节5：自然语言交互（现场输入指令）
#   bash demo_meeting.sh reset  # 清空演示记忆库，恢复到环节3之前的状态
set -euo pipefail
cd "$(dirname "$0")"

export http_proxy=http://127.0.0.1:7897 https_proxy=http://127.0.0.1:7897
export all_proxy=http://127.0.0.1:7897 ALL_PROXY=http://127.0.0.1:7897
export REFLECTION_MODEL_ID=Qwen/Qwen3.5-122B-A10B
# 响应缓存默认开启：排练过的环节现场即使 API 抖动也能复现

PY=/home/yeliheng/miniconda3/envs/graspnet/bin/python
MEM=logs/reflection/demo_meeting/experiences.sqlite3
OUT=logs/reflection/demo_meeting
TS=$(date +%H%M%S)
LLM="--reflector llm --visual-verify"

case "${1:-}" in
  1) $PY -m reflection --viewer --fault none --method baseline \
        --instruction "把红色方块放进蓝色箱子" --context meeting \
        --memory $MEM --output $OUT/live_01_normal_$TS ;;
  2) $PY -m reflection --viewer --fault collision --method reflection_memory $LLM \
        --instruction "把红色方块放进蓝色箱子" --context meeting-collision \
        --memory $MEM --output $OUT/live_02_collision_$TS ;;
  3) $PY -m reflection --viewer --fault collision --method reflection_memory $LLM \
        --instruction "把红色方块放进蓝色箱子" --context meeting-collision \
        --memory $MEM --output $OUT/live_03_memory_$TS ;;
  4) $PY -m reflection --viewer --fault placement --method reflection $LLM \
        --instruction "把红色方块放进蓝色箱子" --context meeting-placement \
        --memory $MEM --output $OUT/live_04_placement_$TS ;;
  5) $PY -m reflection --interactive --viewer --fault none --method reflection $LLM \
        --task-parser llm --context meeting-chat --memory $MEM --output $OUT/live_05_chat_$TS ;;
  reset) rm -f $MEM; echo "演示记忆库已清空" ;;
  *) sed -n 2,9p "$0"; exit 1 ;;
esac
