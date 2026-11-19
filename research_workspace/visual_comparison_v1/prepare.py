import json
import os
import re
from pathlib import Path
from f_common import read, save, sha
from collection_common import verify
from vc_inputs import collect

ROOT = Path(__file__).resolve().parent


def lines(path):
    with path.open(encoding='utf-8') as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write(path, rows):
    with path.open('x', encoding='utf-8') as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False)+'\n')


def main():
    assert os.environ.get('SLURM_JOB_ID')
    export_job = os.environ['RECOVERY_EXPORT_JOB']
    assert re.fullmatch(r'\d+', export_job)
    source = ROOT.parent/'recovery_dataset_v1/exports'/('job_'+export_job)
    manifest = verify(source/'manifest.json')
    assert all(sha(source/p) == h for p, h in manifest['outputs'].items())
    assert manifest['gate']['quantitative_ready'], 'Wait for original quantitative gate'
    inputs, private = collect(lines(source/'outcomes.jsonl'), lines(source/'dev.jsonl'))
    output = ROOT/'prepared'/('export_'+export_job)
    output.mkdir(parents=True, exist_ok=False)
    write(output/'inputs.jsonl', inputs)
    write(output/'private_outcomes.jsonl', private)
    paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'), ROOT/'PLAN.md', source/'manifest.json',
        output/'inputs.jsonl', output/'private_outcomes.jsonl', ROOT.parent/'candidate_sft_v2/manifest.json']
    save(output/'manifest.json', dict(identities={str(p): sha(p) for p in paths},
        export_job=export_job, input_count=len(inputs), max_generations=len(inputs),
        seed=42, max_new_tokens=2048, adapter_enabled=False, training_updates=0,
        test_used=False, scope='all_deduplicated_dev_natural_inputs_and_exported_dev_stops'))
    print(dict(output=str(output), inputs=len(inputs)), flush=True)


if __name__ == '__main__':
    main()
