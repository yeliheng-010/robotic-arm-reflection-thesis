"""在任何GPU训练前固定数据、权重、tokenizer和训练实现。"""
import json
from data import ROOT,DATA,MODEL,read,save,sha


def main():
    preflight = read(ROOT/'data_preflight.json')
    assert preflight['splits']['train']['n']==159
    files = list(ROOT.glob('*.py'))+list(ROOT.glob('*.sh'))+list(ROOT.glob('*.sbatch'))
    files += list(ROOT.glob('*_encoded.json'))+[ROOT/'data_preflight.json',DATA/'manifest.json']
    files += [p for p in MODEL.iterdir() if p.is_file()]
    files += [ROOT.parent/'stability_20261019/stability'/name
              for name in ('sft_model.py','sft_data.py')]
    config = dict(model=str(MODEL),dataset=str(DATA),seed=42,rank=8,learning_rate=1e-4,
                  epochs=1,accumulation=8,train_samples=159,amp_init_scale=32,
                  max_length=max(r['max'] for r in preflight['splits'].values()),
                  quantization='NF4 double quantization, FP16 compute',
                  target='action_id only; conservative rule/hybrid supervised candidate selection',
                  teacher='qwen3.8-flash-next retained as separate inference baseline',
                  test_used=False,identities={str(p):sha(p) for p in sorted(set(files))})
    assert not (ROOT/'manifest.json').exists(), 'Do not overwrite a frozen run'
    save(ROOT/'manifest.json',config)
    print(json.dumps({k:v for k,v in config.items() if k!='identities'}),flush=True)


if __name__=='__main__':
    main()
