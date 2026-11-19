"""所有GPU执行前冻结训练目标、成功集合、旧模型与实现。"""
import json
from set_common import ROOT, OLD, REVIEW, MODEL, read, save, sha, reviewed_sources


def main():
    source = reviewed_sources()
    preflight = read(ROOT/'data_preflight.json')
    assert preflight['splits']['train']['inputs'] == 189
    assert preflight['splits']['train']['responses'] == 197
    identities = dict(read(OLD/'manifest.json')['identities'])
    for section in ('code', 'inputs', 'artifacts'):
        identities.update(source[section])
    files = list(ROOT.glob('*.py'))+list(ROOT.glob('*.sh'))+list(ROOT.glob('*.sbatch'))
    files += [ROOT/p for p in ('train.json','train_encoded.json','eval.json','eval_encoded.json','data_preflight.json')]
    files += [OLD/p for p in ('manifest.json','verification.json','training/result.json','training/reference_logits.pt')]
    files += list((OLD/'training/adapter').iterdir())
    files += list((OLD/'evaluation').glob('*/shard_*/result.json'))
    files += [REVIEW/p for p in ('manifest.json','independent_verification.json')]
    identities.update({str(p):sha(p) for p in files if p.is_file()})
    config = dict(model=str(MODEL), seed=42, rank=8, learning_rate=1e-4, epochs=1,
        accumulation=8, train_samples=189, train_responses=197, optimizer_updates=24,
        amp_init_scale=32, max_length=max(s['max_tokens'] for s in preflight['splits'].values()),
        objective='mean_inputs_mean_successes_mean_tokens', init='base_model_fresh_lora',
        quantization='NF4 double quantization, FP16 compute', test_used=False,
        evaluation_counts=dict(dev=55, legacy_dev=63, train_diagnostic=30),
        diagnostic_counts=dict(dev=49, legacy_dev=29), identities=identities)
    assert not (ROOT/'manifest.json').exists(), 'Never replace a frozen run'
    save(ROOT/'manifest.json', config)
    print(json.dumps({k:v for k,v in config.items() if k != 'identities'}), flush=True)


if __name__ == '__main__':
    main()
