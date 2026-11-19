"""Actual offscreen rendering and physical task acceptance on the deployment host."""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from reflection.__main__ import bootstrap
bootstrap()
from experiments.run_suite import preflight
from reflection.engine import FeedbackEngine
from reflection.reflector import RuleReflector

root = Path('/home/yeliheng/grasp_server')
info = preflight([{'reflector': 'rule', 'segmentation': 'simulation'}])
engine = FeedbackEngine(reflector=RuleReflector(), headless=True, task_parser='rule')
try:
    result = engine.run(method='reflection', fault='collision', source='RedBlock', destination='BlueBin',
        output=root/'preflight_collision', instruction='把红色方块放进蓝色箱子')
finally:
    engine.close()
info['physical_task'] = {k: result[k] for k in ('success', 'attempts', 'elapsed_s')}
info['slurm_job_id'] = os.environ.get('SLURM_JOB_ID')
(root/'preflight.json').write_text(json.dumps(info, ensure_ascii=False, indent=2))
if not result['success']:
    raise RuntimeError('Headless physical acceptance task failed')
print(json.dumps(info, ensure_ascii=False), flush=True)
