#!/bin/bash
#SBATCH --job-name=od-preflight
#SBATCH --partition=batch
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=6G
#SBATCH --time=00:30:00
#SBATCH --output=/home/yeliheng/grasp_server/observation_decision_diagnostic_v2/preflight-%j.log
set -euo pipefail
source /home/yeliheng/grasp_server/observation_decision_diagnostic_v2/environment.sh
cd /home/yeliheng/grasp_server/observation_decision_diagnostic_v2
/home/yeliheng/grasp_server/env_sim/bin/python -m unittest discover -p 'test_*.py' -v
/home/yeliheng/grasp_server/env_sim/bin/python -c 'import ast,pathlib; [ast.parse(p.read_text()) for p in pathlib.Path(".").glob("*.py")]; print("Syntax checked")'
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from od_source import inventory; from od_common import ROOT,save; from od_records import tasks,prepare; value=inventory(); save(ROOT/"preflight_inputs.json",value); save(ROOT/"preflight_prompts.json",[prepare(t) for t in tasks(value)]); print("Source reaudited and CPU prompts prepared")'
/home/yeliheng/grasp_server/qwen35/env/bin/python -c 'import model_run; from od_common import ROOT,read; from od_records import tasks,prepare; inputs=tasks(read(ROOT/"preflight_inputs.json")); actual=[prepare(t) for t in inputs]; assert actual==read(ROOT/"preflight_prompts.json"),"Cross-environment prompts changed"; print("MODEL_ENV_ALL_INPUTS_MATCH",len(inputs))'
/home/yeliheng/grasp_server/env_sim/bin/python od_common.py
cd /tmp
/home/yeliheng/grasp_server/env_sim/bin/python -c 'from od_common import verify; print("FROZEN",len(verify()["cases"]))'
