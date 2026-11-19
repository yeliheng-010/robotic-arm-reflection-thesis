"""正式重载通过后，固定唯一公开输入与训练产物身份。"""
from pathlib import Path
from ac_common import ROOT, TRAINING, common, locations, lines
from f_response import MAX_TOKENS, SEED


def main():
    common.job('SLURM_JOB_ID')
    common.verify(ROOT / 'source_manifest.json')
    output, base = locations()
    checkpoint_job = common.job('CHECKPOINT_REVIEW_JOB')
    checkpoint = ROOT.parent / 'visual_checkpoint_review_v1' / 'results' / ('job_'+checkpoint_job) / 'result.json'
    reviewed = common.verify(checkpoint)
    assert reviewed['passed'] and reviewed['independent_process']
    assert reviewed['manifest_sha256'] == common.sha(TRAINING / 'manifest.json')
    trained = common.verify(TRAINING / 'training' / 'result.json')
    assert trained['status'] == 'completed'
    source = common.verify(base / 'manifest.json')
    report = common.verify(base / 'report.json')
    assert source['max_new_tokens'] == MAX_TOKENS and source['seed'] == SEED
    inputs = lines(base / 'inputs.jsonl')
    assert source['input_count'] == report['inputs'] == len(inputs)
    paths = [ROOT / 'source_manifest.json', TRAINING / 'manifest.json',
        TRAINING / 'training' / 'result.json', checkpoint, base / 'manifest.json',
        base / 'inputs.jsonl', base / 'report.json', *map(Path, trained['identities'])]
    output.mkdir(parents=True, exist_ok=False)
    common.save(output / 'manifest.json', dict(base=str(base), input_count=len(inputs),
        max_generations=len(inputs), max_new_tokens=MAX_TOKENS, seed=SEED,
        adapter_enabled=True, test_used=False,
        identities={str(p): common.sha(p) for p in paths}))
    print(dict(prepared=str(output), inputs=len(inputs)), flush=True)


if __name__ == '__main__':
    main()
