"""冻结24个诊断条目，原模型/协议/基线只读。"""
from pathlib import Path
from common import ROOT,PREVIOUS,METHODS,SCENES,MISSING_SCENES,read,save,sha,is_smoke,verify


def entries_for(previous):
    entries=[]
    for variant,scenes,budget in (('budget4',SCENES,4),('no_missing',MISSING_SCENES,3)):
        for scene in scenes:
            for method in METHODS:
                old=next(e for e in previous['entries'] if e['uid']==scene+'__'+method)
                assert old['eligible']
                entries.append(dict(old,source_uid=old['uid'],uid=old['uid']+'__'+variant,
                                    variant=variant,max_attempts=budget))
    assert len(entries)==24 and sum(is_smoke(e) for e in entries)==8
    return entries


def main():
    assert not (ROOT/'manifest.json').exists()
    previous=read(PREVIOUS/'manifest.json')
    verification=read(PREVIOUS/'verification.json')
    assert verification['passed'] and verification['complete']
    identities=dict(previous['identities'])
    assert all(sha(p)==h for p,h in identities.items()), 'Previous frozen source changed'
    entries=entries_for(previous)
    files=list(ROOT.glob('*.py'))+list(ROOT.glob('*.sh'))+list(ROOT.glob('*.sbatch'))
    files += [PREVIOUS/'manifest.json',PREVIOUS/'verification.json']
    for entry in entries:
        folder=PREVIOUS/'tasks'/entry['source_uid']
        result=read(folder/'result.json')
        files += [folder/'result.json',folder/'summary.json']
        files += [Path(s['result_path']) for s in result['attempts']]
        files += [PREVIOUS/'service/requests'/f"{d['event']['response']['id']}.json"
                  for d in result['decisions'] if 'event' in d and 'response' in d['event']]
    identities.update({str(p):sha(p) for p in set(files)})
    save(ROOT/'manifest.json',dict(entries=entries,identities=identities,expected=24,
        max_physical=88,conditions=4,test_used=False,training_approved=False,
        parent_manifest_sha256=sha(PREVIOUS/'manifest.json')))
    verify()
    print(dict(frozen=True,expected=24,smoke=8,max_physical=88,manifest_sha256=sha(ROOT/'manifest.json')))


if __name__=='__main__':
    main()
