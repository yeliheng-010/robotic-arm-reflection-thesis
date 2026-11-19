"""Read current deployment state without loading any model or allocating a GPU."""
import json
from pathlib import Path
import subprocess

root = Path('/home/yeliheng/grasp_server')
report = {}
for name in ('migration.json', 'jobs.json', 'preflight.json', 'latest_collection.json'):
    path = root/name
    if path.exists():
        report[name] = json.loads(path.read_text())
if 'latest_collection.json' in report:
    path = Path(report['latest_collection.json']['output'])/'status.json'
    if path.exists():
        report['collection'] = json.loads(path.read_text())
for path in sorted((root/'qwen35/runs').glob('*/smoke_result.json')):
    result = json.loads(path.read_text())
    report['latest_qwen35_smoke'] = {k: result.get(k) for k in (
        'status', 'error', 'peak_allocated_bytes', 'trainable_parameters', 'changed_adapter_tensors',
        'adapter_reload_max_logit_error', 'adapter_path')}
for name, command in (
    ('slurm', ['squeue', '-h', '-u', 'yeliheng', '-o', '%i %j %T %b %M %R']),
    ('gpus', ['nvidia-smi', '--query-gpu=index,name,memory.used,memory.free', '--format=csv,noheader'])):
    result = subprocess.run(command, capture_output=True, text=True)
    report[name] = result.stdout.strip()
print(json.dumps(report, ensure_ascii=False, indent=2))
