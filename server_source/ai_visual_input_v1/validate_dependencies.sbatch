#!/bin/bash
#SBATCH --job-name=visual-overlay-import-check
#SBATCH --partition=batch
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:05:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_visual_input_v1/dependency-check-%j.log
set -euo pipefail
export PYTHONPATH=${PYTHONPATH:-}
source /home/yeliheng/grasp_server/candidate_sft_v2/environment.sh
export PYTHONPATH=/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay:$PYTHONPATH
/home/yeliheng/grasp_server/qwen35/env/bin/python -B -c "import torch, torchvision; assert torch.__version__ == '2.6.0+cu124'; assert torchvision.__version__ == '0.21.0+cu124'; print({'torch': torch.__version__, 'torchvision': torchvision.__version__, 'path': torchvision.__file__})"
