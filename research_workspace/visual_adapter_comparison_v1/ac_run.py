"""每个公开输入只生成一次；私有执行后果只交给后处理。"""
import traceback
from ac_common import ROOT, common, locations, lines
from ac_generator import AdapterGenerator
from sv_strategy_actions import validate


def execute(generator, row, output):
    assert set(row) == {'input_id', 'request', 'messages', 'images', 'image_sha256'}
    assert len(row['images']) == len(row['image_sha256']) == 2
    assert all(common.sha(p) == h for p, h in zip(row['images'], row['image_sha256']))
    folder = output / row['input_id']
    folder.mkdir(exist_ok=False)
    values, stats = generator.prepare_images(row['messages'], row['images'])
    common.save(folder / 'generation_started.json', dict(input_id=row['input_id'], stats=stats, calls=1))
    response = generator.generate(values)
    common.save(folder / 'response.json', response)
    parsed = validate(response, row['request'], mode='direct')
    result = dict(input_id=row['input_id'], validation=parsed,
        response_sha256=common.sha(folder / 'response.json'))
    common.save(folder / 'result.json', result)
    print(dict(input_id=row['input_id'], valid=parsed['valid'], finish=response['finish_reason']), flush=True)
    return result


def main():
    common.job('SLURM_JOB_ID')
    common.verify(ROOT / 'source_manifest.json')
    prepared, base = locations()
    manifest = common.verify(prepared / 'manifest.json')
    output = prepared / 'adapter_comparison'
    output.mkdir(exist_ok=False)
    try:
        inputs = lines(base / 'inputs.jsonl')
        assert len(inputs) == manifest['max_generations']
        generator = AdapterGenerator()
        common.save(output / 'model_identity.json', dict(identity=generator.identity,
            environment=generator.environment))
        rows = [execute(generator, row, output) for row in inputs]
        common.verify(prepared / 'manifest.json')
        common.save(output / 'complete.json', dict(passed=True, model_calls=len(rows), rows=rows,
            manifest_sha256=common.sha(prepared / 'manifest.json'), training_updates=0, physical_attempts=0))
    except BaseException as error:
        common.save(output / 'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise


if __name__ == '__main__':
    main()
