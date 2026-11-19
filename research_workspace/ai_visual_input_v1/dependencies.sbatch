#!/bin/bash
#SBATCH --job-name=visual-isolated-dependency
#SBATCH --partition=batch
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=00:15:00
#SBATCH --output=/home/yeliheng/grasp_server/ai_visual_input_v1/dependency-%j.log
set -euo pipefail
cd /home/yeliheng/grasp_server/ai_visual_input_v1
test ! -e torchvision_overlay
/home/yeliheng/grasp_server/qwen35/env/bin/python -m pip --isolated install --no-deps --target torchvision_overlay --index-url https://download.pytorch.org/whl/cu124 'torchvision==0.21.0+cu124'
PYTHONPATH=/home/yeliheng/grasp_server/ai_visual_input_v1/torchvision_overlay /home/yeliheng/grasp_server/qwen35/env/bin/python -B -c "import torch, torchvision; assert torch.__version__ == '2.6.0+cu124'; assert torchvision.__version__ == '0.21.0+cu124'; print({'torch': torch.__version__, 'torchvision': torchvision.__version__, 'path': torchvision.__file__})"
