"""生成前工程中止的独立CPU审计；不加载权重或调用generate。"""
import os
from pathlib import Path
import torch
from qualified_prompt_checkpoint_v1.protocol import ROOT, PROJECT, RUN, read, save, sha, verify
from qualified_prompt_checkpoint_v1.audit import request_check, tensor_check


def main():
    manifest = verify()
    request, _ = request_check(manifest)
    _, encoding = tensor_check(request)
    absent = ['generation_started.json', 'response.json', 'result.json', 'generation_config.json']
    assert all(not (RUN / name).exists() for name in absent)
    assert read(RUN / 'model_claim.json')['consumed'] == 1
    log = (ROOT / 'run-6811.log').read_text(encoding='utf-8')
    missing = PROJECT / 'improvement_20261019/code/_classes.py'
    assert 'AssertionError: ' + str(missing) in log and not missing.exists()
    synthetic = {name: dict(raw_file=getattr(module, '__file__', None), instance_file=vars(module).get('__file__'), module_type=type(module).__name__)
                 for name, module in [('torch.classes', torch.classes), ('torch.ops', torch.ops)]}
    assert synthetic['torch.classes']['raw_file'] == '_classes.py'
    source = (ROOT / 'model.py').read_text(encoding='utf-8')
    assert source.index('record(generator, values') < source.index("save(RUN / 'generation_started.json'")
    assert source.index("save(RUN / 'generation_started.json'") < source.index('generator.generate(values)')
    save(RUN / 'failure_audit.json', dict(passed=True, job=os.environ['SLURM_JOB_ID'],
         failure_stage='pre_generation_source_provenance', model_reservations=1, generations_started=0,
         responses_saved=0, model_calls=0, physical=0, training=0,
         full_tensor_reencoding_equal=True, input_tokens=encoding['encoding']['input_tokens'],
         synthetic_modules=synthetic, missing_path=str(missing), missing_path_exists=False,
         absent_files=absent, model_source_sha256=sha(ROOT / 'model.py'),
         failure_log_sha256=sha(ROOT / 'run-6811.log'), auditor_sha256=sha(Path(__file__)),
         auditor_sbatch_sha256=sha(ROOT / 'failure_audit_v2.sbatch'), frozen_identities=len(manifest['identities'])))
    print(dict(passed=True, actual_generations=0, cause='synthetic_torch_module_file'), flush=True)


if __name__ == '__main__':
    main()
