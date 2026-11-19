"""事前固定全部开发条件、来源记录和执行代码。"""
import importlib
from pathlib import Path
from common import ROOT,PARENT,SFT,NEW_SFT,METHODS,EXPECTED,SMOKE_EXPECTED,read,save,sha,is_smoke


def parent_code(value):
    paths=[]
    if isinstance(value,dict):
        paths.extend(value.get('code',{}).keys())
        for key,child in value.items():
            if key!='code' and isinstance(child,dict):
                paths.extend(parent_code(child))
    return paths


def entries_for(batch,package):
    protocol=importlib.import_module(package+'.protocol').verify()
    qualification=importlib.import_module(package+'.tasks').qualification
    entries=[]
    for item in protocol['items']:
        if item['split']!='development_validation' or item['arm']!='new_rule':
            continue
        qualified=qualification(item)
        for method in METHODS:
            current=dict(item,arm='new_rule' if method=='rule' else 'hybrid')
            current['id']=item['scene_id']+'_'+current['arm']
            entries.append(dict(uid=item['scene_id']+'__'+method,batch=batch,package=package,
                method=method,item=current,eligible=qualified['eligible'],qualification_status=qualified['status']))
    return entries


def main():
    trained=read(SFT/'verification.json')
    assert trained['passed'] and trained['after']['reload_errors']==[0,0,0]
    new=read(NEW_SFT/'verification.json')
    assert new['passed'] and new['complete'] and new['reload_errors']['new']==[0,0,0]
    entries=entries_for('scene_expansion_v1','expand')+entries_for('hard_cases_v1','hardstudy')
    assert len(entries)==EXPECTED and len({r['item']['scene_id'] for r in entries})==60
    assert sum(is_smoke(r) for r in entries)==SMOKE_EXPECTED
    files=list(ROOT.glob('*.py'))+list(ROOT.glob('*.sh'))+list(ROOT.glob('*.sbatch'))
    for directory in (SFT,NEW_SFT):
        files += [directory/'manifest.json',directory/'verification.json',directory/'training/result.json',
                  directory/'training/reference_logits.pt']
        files += list((directory/'training/adapter').glob('*'))
        files += [Path(p) for p in read(directory/'manifest.json')['identities']
                  if Path(p).suffix in ('.py','.sh')]
    files += [SFT/'dev_encoded.json',NEW_SFT/'eval.json',NEW_SFT/'eval_encoded.json']
    files += list((NEW_SFT/'evaluation').glob('*/shard_*/result.json'))
    files += [PARENT/'route_loop_v1/verify.py',PARENT/'route_loop_v1/compare.py',
              PARENT/'noisy_loop_v1/verify.py']
    for batch in ('scene_expansion_v1','hard_cases_v1'):
        files.append(PARENT/batch/'protocol.json')
        files.extend(Path(p) for p in parent_code(read(PARENT/batch/'protocol.json')))
    for entry in entries:
        folder=PARENT/entry['batch']/'qualification'/entry['item']['scene_id']
        files.extend([folder/'result.json',folder/'summary.json'])
    manifest=dict(entries=entries,max_attempts=3,expected=EXPECTED,conditions=60,test_used=False,
                  parent_training_sha256=sha(SFT/'manifest.json'),
                  new_training_sha256=sha(NEW_SFT/'manifest.json'),
                  identities={str(p):sha(p) for p in sorted(set(files)) if p.is_file()})
    assert not (ROOT/'manifest.json').exists()
    save(ROOT/'manifest.json',manifest)
    print(dict(expected=EXPECTED,conditions=60,smoke=SMOKE_EXPECTED,eligible=sum(r['eligible'] for r in entries)))


if __name__=='__main__':
    main()
