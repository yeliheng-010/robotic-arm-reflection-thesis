"""真实已审计两图样本的只读前向检查；不生成、不更新参数。"""
import math
import os
import sys
import traceback
from pathlib import Path
import torch
from transformers import AutoProcessor
import runtime
from encoding import encode
from vt_objective import objective, move
from collection_common import read, save, sha, verify

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'recovery_collection_v1/batches/000/physics'
sys.path.insert(0, str(ROOT.parent/'recovery_dataset_v1'))
from export_records import record
from rc_review import decisions


def audited_record():
    name = 'R0_964006_varied_noisy'
    audit_path = SOURCE/'audits'/(name+'.json')
    audit = verify(audit_path)
    assert audit['passed'] and audit['manifest_sha256'] == sha(SOURCE/'manifest.json')
    manifest = verify(SOURCE/'manifest.json')
    case = next(c for c in manifest['cases'] if c['item']['id'] == name)
    path = SOURCE/'cases'/name/'lower_then_slow/result.json'
    assert sha(path) == audit['identities'][str(path)]
    rows = decisions(case, read(path))
    assert len(rows) == 1 and rows[0]['verified_recovery']
    return record(rows[0]), audit_path


def main():
    assert os.environ.get('SLURM_JOB_ID')
    assert runtime.__file__.endswith('/candidate_sft_v2/runtime.py'), runtime.__file__
    output = ROOT/'forward_checks'/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    try:
        row, audit_path = audited_record()
        config = runtime.verify_manifest()
        processor = AutoProcessor.from_pretrained(config['model'], local_files_only=True,
            trust_remote_code=False, min_pixels=128*128, max_pixels=448*448)
        values, stats = encode(processor, row['messages'])
        model, params, _, environment = runtime.setup(config)
        before = {n: p.detach().cpu().clone() for n, p in params.items()}
        model.eval()
        with model.disable_adapter(), torch.inference_mode(), torch.autocast('cuda', dtype=torch.float16):
            loss = float(objective(model, move(values)))
        assert math.isfinite(loss)
        assert all(torch.equal(before[n], p.detach().cpu()) for n, p in params.items())
        paths = [*ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch'),
            audit_path, Path(row['source_input']), ROOT.parent/'visual_sft_v1/encoding.py']
        result = dict(passed=True, loss=loss, stats=stats, environment=environment,
            training_updates=0, model_generations=0, forward_calls=1, adapter_enabled=False,
            source_input=row['source_input'], parameters_unchanged=True,
            identities={str(p): sha(p) for p in paths},
            limitation='One real forward pass verifies computation only, not learning or physical improvement')
        save(output/'result.json', result)
        print(dict(passed=True, loss=loss, stats=stats, training_updates=0, model_generations=0), flush=True)
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
