#!/usr/bin/env bash
set -euo pipefail
cd /home/yeliheng/VLM_Grasp_Interactive
ROOT_SIM=/home/yeliheng/grasp_server
mkdir -p "$ROOT_SIM"
/home/yeliheng/grasp_qlora/env/bin/python -m venv --system-site-packages "$ROOT_SIM/env_sim"
"$ROOT_SIM/env_sim/bin/python" -m pip install --retries 3 --timeout 60 -r training/server/requirements-sim.txt
"$ROOT_SIM/env_sim/bin/python" -m pip freeze > "$ROOT_SIM/sim_packages.txt"
touch "$ROOT_SIM/sim_setup_complete"
