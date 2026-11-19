"""全索引覆盖、相同冻结模型及独立重载后才报告前后效果。"""
import json
from data import ROOT,SPLITS,read,save,sha,load_split
from runtime import verify_manifest


def merged(mode):
    rows,errors = [],[]
    for shard in range(3):
        path = ROOT/'evaluation'/mode/f'shard_{shard}'/'result.json'
        result = read(path)
        assert result['status']=='completed' and result['manifest_sha256']==sha(ROOT/'manifest.json')
        rows.extend(result['rows'])
        if mode=='after':
            errors.append(result['reload_error'])
    metrics = {}
    for split in ('dev','legacy_dev'):
        group = sorted([r for r in rows if r['split']==split],key=lambda r:r['index'])
        _,index = load_split(split)
        assert [r['index'] for r in group]==list(range(SPLITS[split]))
        assert [r['id'] for r in group]==[r['id'] for r in index]
        tokens = sum(r['supervised_tokens'] for r in group)
        metrics[split] = dict(n=len(group),**{k:sum(r[k] for r in group)
                              for k in ('json_valid','candidate_valid','target_match')},
                              loss=sum(r['loss']*r['supervised_tokens'] for r in group)/tokens)
    assert len(rows)==78
    return dict(metrics=metrics,reload_errors=errors)


def main():
    verify_manifest()
    training = read(ROOT/'training/result.json')
    assert training['status']=='completed' and training['samples_seen']==159
    updates = read(ROOT/'training/updates.json')
    assert len(updates)==20 and sorted(i for u in updates for i in u['indices'])==list(range(159))
    summary = dict(passed=True,training=training,before=merged('before'),after=merged('after'),
                   physics_evaluated=False,test_used=False,
                   identity='Qwen3.5-4B student, not Flash-Next fine-tuning')
    save(ROOT/'verification.json',summary)
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        save(ROOT/'verification_failure.json',dict(passed=False,error=repr(error)))
        raise
