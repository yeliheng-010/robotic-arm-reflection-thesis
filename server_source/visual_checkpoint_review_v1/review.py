"""独立进程重载最终 adapter；没有优化器、生成或仿真。"""
import os
import sys
import traceback
from pathlib import Path
import torch

ROOT = Path(__file__).resolve().parent
TRAINING = ROOT.parent / 'visual_finetune_v1'
sys.path.insert(0, str(TRAINING))
import vf_common_v2 as common
import smoke_v2
assert Path(common.__file__).resolve().parent == TRAINING
assert Path(smoke_v2.__file__).resolve().parent == TRAINING
from review_policy import validate_training, compare_logits


def load_training(settings):
    folder = TRAINING / 'training'
    result = common.verify(folder / 'result.json')
    paths = sorted((folder / 'updates').glob('*.json'))
    updates = [common.read(p) for p in paths]
    validate_training(result, updates, settings=settings,
        manifest_sha256=common.sha(TRAINING / 'manifest.json'))
    order = common.read(folder / 'epoch_order.json')
    assert order == [row['indices'] for row in updates]
    return folder, result, paths


def run_review():
    common.verify(ROOT / 'source_manifest.json')
    settings = common.config()
    folder, result, update_paths = load_training(settings)
    row = next(r for r in common.rows(settings) if r['input_id'] == result['reference_input'])
    values = common.encoded(row, common.processor(settings))
    model, _, _, environment = common.runtime.setup(settings, adapter=folder / 'adapter')
    actual = smoke_v2.probe(model, values)
    expected = torch.load(folder / 'reference_logits.pt', weights_only=True)
    error = compare_logits(expected, actual)
    common.verify(folder / 'result.json')
    common.config()
    common.verify(ROOT / 'source_manifest.json')
    paths = [ROOT / 'source_manifest.json', TRAINING / 'manifest.json',
        folder / 'result.json', *update_paths]
    return dict(passed=True, independent_process=True, reload_max_logit_error=error,
        train_updates=result['updates'], samples_seen=result['samples_seen'],
        changed_tensors=result['changed_tensors'], environment=environment,
        manifest_sha256=result['manifest_sha256'], model_generations=0,
        new_training_updates=0, physical_attempts=0, test_used=False,
        identities={str(p): common.sha(p) for p in paths},
        limitation='Reload validity is not improved policy or physical recovery performance')


def main():
    job = common.job('SLURM_JOB_ID')
    output = ROOT / 'results' / ('job_' + job)
    output.mkdir(parents=True, exist_ok=False)
    try:
        result = run_review()
        common.save(output / 'result.json', result)
        print(result, flush=True)
    except BaseException as error:
        common.save(output / 'failure.json', dict(error=repr(error),
            traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
