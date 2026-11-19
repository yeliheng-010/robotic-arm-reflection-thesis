"""独立进程加载同一基础权重，按索引分片做完整开发生成。"""
import argparse
import json
import os
import time
import traceback
import torch
from data import ROOT,read,save,sha,load_split
from runtime import verify_manifest,setup,predict
from smoke import probe


def evaluate(mode,shard,shards):
    config = verify_manifest()
    adapter = None
    if mode=='after':
        trained = read(ROOT/'training/result.json')
        assert trained['status']=='completed' and trained['manifest_sha256']==sha(ROOT/'manifest.json')
        adapter = ROOT/'training/adapter'
        assert all(sha(adapter/n)==h for n,h in trained['adapter_files'].items())
    output = ROOT/'evaluation'/mode/f'shard_{shard}'
    output.mkdir(parents=True,exist_ok=False)
    model,_,tok,environment = setup(config,adapter=adapter)
    reload_error = None
    if mode=='after':
        expected = torch.load(ROOT/'training/reference_logits.pt',weights_only=True)
        actual = probe(model,read(ROOT/'dev_encoded.json')[0])
        reload_error = float((expected-actual).abs().max())
        assert reload_error<=1e-4, f'Trained adapter reload mismatch: {reload_error}'
    rows,started = [],time.monotonic()
    try:
        for split in ('dev','legacy_dev'):
            encoded = read(ROOT/f'{split}_encoded.json')
            raw,index = load_split(split)
            for i in range(shard,len(raw),shards):
                result = predict(model,tok,encoded[i],raw=raw[i],baseline=mode=='before')
                result.update(split=split,index=i,id=index[i]['id'])
                rows.append(result)
                save(output/'progress.json',dict(status='running',rows=rows,
                     elapsed_s=time.monotonic()-started,job=os.environ['SLURM_JOB_ID']))
                print(json.dumps(dict(mode=mode,shard=shard,split=split,index=i,
                                      valid=result['candidate_valid'],match=result['target_match'])),flush=True)
        save(output/'result.json',dict(status='completed',rows=rows,shard=shard,shards=shards,
             environment=environment,elapsed_s=time.monotonic()-started,
             reload_error=reload_error,manifest_sha256=sha(ROOT/'manifest.json'),test_used=False))
    except BaseException as error:
        save(output/'failure.json',dict(error=repr(error),traceback=traceback.format_exc()))
        raise


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode',choices=['before','after'])
    parser.add_argument('--shard',type=int,required=True)
    parser.add_argument('--shards',type=int,default=3)
    args = parser.parse_args()
    assert 0<=args.shard<args.shards
    evaluate(args.mode,args.shard,args.shards)
