"""唯一真实生成；所有终止结果均不补抽，不调用规划或仿真。"""
import json
import os
from qualified_prompt_checkpoint_v1.protocol import RUN, read, save, sha, verify, reserve, classify
from qualified_prompt_checkpoint_v1.provenance import record


def main():
    assert os.environ.get('SLURM_JOB_ID')
    reserve()
    manifest = read(RUN / 'manifest.json')
    save(RUN / 'call_started.json', dict(job=os.environ['SLURM_JOB_ID'],
         request_sha256=sha(RUN / 'request.json'), ordinal=1))
    from mm_generator import VisualGenerator
    generator = VisualGenerator()
    assert generator.identity['adapter_enabled'] is False
    request = read(RUN / 'request.json')
    values, encoding = generator.prepare_images(request['messages'], [request['image']])
    record(generator, values, manifest=manifest, encoding=encoding)
    save(RUN / 'generation_started.json', dict(ordinal=1, input_tensors_sha256=sha(RUN / 'input_tensors.npz')))
    response = generator.generate(values)
    save(RUN / 'response.json', response)
    result = classify(response, json.loads(request['messages'][1]['content'])['history'])
    save(RUN / 'result.json', dict(**result, model_calls=1, planning=0, physical=0, training=0,
         safety_evaluated=False, ready=False, retries=0))
    verify()
    print(dict(status=result['status'], action=result['action'], input_tokens=response['prompt_tokens'],
               output_tokens=response['completion_tokens'], model_calls=1, physical=0), flush=True)


if __name__ == '__main__':
    main()
