"""真实两图反向通路检查；不创建优化器，不更新模型参数。"""
import math
import os
import traceback
from pathlib import Path
import torch
from transformers import AutoProcessor
import runtime
from encoding import encode
from vt_objective import objective, move
from forward_check import audited_record
from f_common import save, sha

ROOT = Path(__file__).resolve().parent
GRADIENT_SCALE = 32.


def main():
    assert os.environ.get('SLURM_JOB_ID')
    assert runtime.__file__.endswith('/candidate_sft_v2/runtime.py')
    output = ROOT/'gradient_checks'/('job_'+os.environ['SLURM_JOB_ID'])
    output.mkdir(parents=True, exist_ok=False)
    try:
        row, audit = audited_record()
        config = runtime.verify_manifest()
        proc = AutoProcessor.from_pretrained(config['model'], local_files_only=True,
            trust_remote_code=False, min_pixels=128*128, max_pixels=448*448)
        values, stats = encode(proc, row['messages'])
        model, params, _, environment = runtime.setup(config)
        original = {n: p.detach().cpu().clone() for n, p in params.items()}
        model.train()
        model.zero_grad(set_to_none=True)
        with torch.autocast('cuda', dtype=torch.float16):
            loss = objective(model, move(values))
        assert math.isfinite(float(loss.detach()))
        (loss * GRADIENT_SCALE).backward()
        gradients = {n: p.grad.detach().float()/GRADIENT_SCALE for n, p in params.items() if p.grad is not None}
        assert gradients and all(torch.isfinite(g).all() for g in gradients.values())
        squared = sum(float(g.square().sum()) for g in gradients.values())
        assert math.isfinite(squared) and squared > 0
        assert all(torch.equal(original[n], p.detach().cpu()) for n, p in params.items())
        model.zero_grad(set_to_none=True)
        result = dict(passed=True, loss=float(loss.detach()), gradient_norm=math.sqrt(squared),
            gradient_tensors=len(gradients), trainable_parameters_unchanged=True, stats=stats,
            model_generations=0, optimizer_steps=0, training_updates=0,
            environment=environment, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            identities={str(p): sha(p) for p in (Path(__file__), ROOT/'vt_objective.py',
                ROOT/'forward_check.py', audit, Path(row['source_input']))},
            limitation='One sample gradient computation only, not trained weights or learning evidence')
        save(output/'result.json', result)
        print({k: result[k] for k in ('passed', 'loss', 'gradient_norm', 'gradient_tensors', 'training_updates')}, flush=True)
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
