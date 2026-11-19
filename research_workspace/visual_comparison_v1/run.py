"""只传公开输入；先记生成开始，再保存原始响应，不自动补跑。"""
import os
import re
import sys
import traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'candidate_sft_v2'))
import runtime
assert runtime.__file__.endswith('/candidate_sft_v2/runtime.py'), runtime.__file__
assert sys.modules['loss'].__file__.endswith('/candidate_sft_v2/loss.py')
from mm_generator import VisualGenerator
from sv_strategy_actions import validate, choose, check
from collection_common import save, sha, verify
from prepare import lines

ROOT = Path(__file__).resolve().parent


def execute(generator, row, output):
    assert set(row) == {'input_id', 'request', 'messages', 'images', 'image_sha256'}
    assert all(sha(p) == h for p, h in zip(row['images'], row['image_sha256']))
    folder = output/row['input_id']
    folder.mkdir(exist_ok=False)
    values, stats = generator.prepare_images(row['messages'], row['images'])
    save(folder/'generation_started.json', dict(input_id=row['input_id'], stats=stats, calls=1))
    response = generator.generate(values)
    save(folder/'response.json', response)
    parsed = validate(response, row['request'], mode='direct')
    fixed = choose(row['request'])
    check(fixed, row['request'])
    result = dict(input_id=row['input_id'], validation=parsed, fixed_rule_action=fixed,
        response_sha256=sha(folder/'response.json'))
    save(folder/'result.json', result)
    print(dict(input_id=row['input_id'], valid=parsed['valid'], finish=response['finish_reason']), flush=True)
    return result


def main():
    assert os.environ.get('SLURM_JOB_ID')
    export_job = os.environ['RECOVERY_EXPORT_JOB']
    assert re.fullmatch(r'\d+', export_job)
    prepared = ROOT/'prepared'/('export_'+export_job)
    manifest = verify(prepared/'manifest.json')
    output = prepared/'base_comparison'
    output.mkdir(exist_ok=False)
    try:
        inputs = lines(prepared/'inputs.jsonl')
        assert len(inputs) == manifest['max_generations']
        generator = VisualGenerator()
        save(output/'model_identity.json', dict(identity=generator.identity, environment=generator.environment))
        rows = [execute(generator, row, output) for row in inputs]
        verify(prepared/'manifest.json')
        save(output/'complete.json', dict(passed=True, model_calls=len(rows), rows=rows,
            manifest_sha256=sha(prepared/'manifest.json'), training_updates=0, physical_attempts=0))
    except BaseException as error:
        save(output/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
