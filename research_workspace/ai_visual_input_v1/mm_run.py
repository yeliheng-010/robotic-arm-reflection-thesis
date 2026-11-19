import os
import traceback
from mm_common import ROOT, read, save, sha, verify
from mm_generator import VisualGenerator
from f_response import validate


def main():
    assert os.environ.get('SLURM_JOB_ID')
    verify()
    bundle = read(ROOT/'input.json')
    assert bundle['direct_messages'][1] == bundle['diagnostic_messages'][1]
    model = VisualGenerator()
    save(ROOT/'environment.json', dict(identity=model.identity, environment=model.environment))
    for mode in ('direct', 'diagnostic'):
        save(ROOT/(mode+'_started.json'), dict(mode=mode, input_sha256=sha(ROOT/'input.json')))
        values, encoding = model.prepare_images(bundle[mode+'_messages'], bundle['visual']['paths'])
        save(ROOT/(mode+'_generation_started.json'), dict(mode=mode, encoding=encoding))
        response = model.generate(values)
        checked = validate(response, bundle['request'], mode=mode)
        save(ROOT/(mode+'_response.json'), dict(response=response, validation=checked, encoding=encoding))
        print(dict(mode=mode, validation=checked, encoding=encoding), flush=True)
    verify()
    save(ROOT/'complete.json', dict(model_calls=2, physical_attempts=0, proposals_executed=0, training_runs=0,
        causal_correctness_not_established=True))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'failure.json', dict(error=repr(error), traceback=traceback.format_exc()))
        raise
