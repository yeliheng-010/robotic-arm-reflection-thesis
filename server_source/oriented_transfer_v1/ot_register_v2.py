from ot_register import ROOT,save,sha,verify
RUN=ROOT/'endpoints_v2'


def main():
    previous=verify(ROOT/'endpoints/manifest.json')
    assert not RUN.exists()
    reuse=ROOT/'endpoints/audit/capsule_964347/result.json'
    result=verify(reuse)
    assert result['passed'] and result['safe_grasps']==0 and result['independent']
    identities=dict(previous['identities'])
    paths=[ROOT/'endpoints/manifest.json',reuse,*ROOT.glob('*.py'),*ROOT.glob('*.sh'),*ROOT.glob('*.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(RUN/'manifest.json',dict(rows=previous['rows'][:1],reused=[dict(path=str(reuse),result=result)],
        identities=identities,max_endpoint_checks=4096,max_process_seconds=600,
        physical_attempts=0,model_calls=0,revision='Normalize free-joint quaternion; no tolerance changes'))


if __name__=='__main__':
    main()
