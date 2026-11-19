#!/usr/bin/env bash
set -euo pipefail
/home/yeliheng/grasp_qlora/env/bin/python -m venv --system-site-packages /home/yeliheng/grasp_server/qwen35/env
QPY=/home/yeliheng/grasp_server/qwen35/env/bin/python
"$QPY" -m pip install --retries 3 --timeout 60 torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
"$QPY" -m pip install --retries 3 --timeout 60 transformers==5.20.1 peft==0.21.2 accelerate==1.12.0 bitsandbytes==0.49.2 pillow jinja2
"$QPY" -m pip freeze > /home/yeliheng/grasp_server/qwen35/packages.txt
"$QPY" -c 'import torch,transformers,peft; print(torch.__version__,transformers.__version__,peft.__version__)'
touch /home/yeliheng/grasp_server/qwen35/setup_complete
