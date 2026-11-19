"""独立重读输入、图像身份、EOS、两模式公平性；不把合法假设当正确原因。"""
import os
from pathlib import Path
from f_common import read, save, sha
from f_response import validate, finish
from prompts import messages

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent/'ai_visual_input_v1/temporal_v3'


def main():
    assert os.environ.get('SLURM_JOB_ID')
    manifest = read(SOURCE/'manifest.json')
    assert all(sha(p)==h for p,h in manifest['identities'].items())
    bundle, complete = read(SOURCE/'input.json'), read(SOURCE/'complete.json')
    visual, request = bundle['visual'], bundle['request']
    assert visual['order'] == ['before', 'after'] and len(visual['paths']) == 2
    assert all(sha(p)==h for p,h in zip(visual['paths'], visual['sha256']))
    assert bundle['direct_messages'][1] == bundle['diagnostic_messages'][1]
    assert complete == dict(model_calls=2, physical_attempts=0, proposals_executed=0, training_runs=0,
                            causal_correctness_not_established=True)
    rows = []
    for mode in ('direct', 'diagnostic'):
        assert bundle[mode+'_messages'] == messages(request, mode=mode)
        saved = read(SOURCE/(mode+'_response.json'))
        response, encoding = saved['response'], saved['encoding']
        assert finish(response['generated_ids'], response['eos_ids']) == response['finish_reason'] == 'stop'
        assert len(response['generated_ids']) == response['completion_tokens']
        checked = validate(response, request, mode=mode)
        assert checked == saved['validation'] and checked['valid']
        assert response['identity']['adapter_enabled'] is False
        assert response['identity']['base'] == 'Qwen3.5-4B'
        assert encoding['input_tokens'] == response['prompt_tokens']
        assert len(encoding['image_grid_thw']) == 2 and encoding['pixel_values_shape'][0] > 0
        assert read(SOURCE/(mode+'_started.json'))['input_sha256'] == sha(SOURCE/'input.json')
        assert read(SOURCE/(mode+'_generation_started.json'))['encoding'] == encoding
        rows.append(dict(mode=mode, action=checked['parsed']['action'], encoding=encoding, valid=True))
    files = [p for p in SOURCE.iterdir() if p.is_file()] + [Path(p) for p in visual['paths']]
    save(ROOT/'result.json', dict(passed=True, rows=rows, model_calls=0, source_model_calls=2,
        physical_attempts=0, training_ready=False, causal_correctness_not_established=True,
        identities={str(p):sha(p) for p in files+[Path(__file__)]}))
    print(dict(passed=True, audited_calls=2, new_calls=0, causal_correctness_not_established=True))


if __name__ == '__main__':
    main()
