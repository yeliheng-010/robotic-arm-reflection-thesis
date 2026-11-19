from surface_physical_v1.common import ROOT,TRIAL,STATIC,SOURCE,read,save,sha,verify,selected


def prepare():
    assert not TRIAL.exists()
    previous=verify(STATIC/'manifest.json')
    assert read(STATIC/'audit/result.json')['passed']
    audit=read(STATIC/'paths/audit/result.json')
    assert audit['ready'] and audit['independent']
    identities=dict(previous['identities'])
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sh','.sbatch')]
    paths+=[p for p in (STATIC/'paths').rglob('*.json')]
    paths+=[STATIC/'audit/result.json',STATIC/'probe/result.json']
    identities.update({str(p):sha(p) for p in paths})
    row=dict(case=previous['case'],folder=str(SOURCE),candidate=selected())
    save(TRIAL/'manifest.json',dict(entry=row,cases=[row['case']],identities=identities,
        max_attempts=1,model_calls=0,training_updates=0,independent_new_condition=False,
        scope='One frozen engineering candidate; not model-selected'))
    save(TRIAL/'qualification/964347/result.json',dict(qualified=True,
        manifest_sha256=sha(TRIAL/'manifest.json'),geometry=dict(passed=True,
        status='selected',source=str(STATIC/'paths/audit/result.json'))))


def execution():
    previous=verify(TRIAL/'manifest.json')
    assert read(TRIAL/'preflight_result.json')['passed']
    assert read(TRIAL/'preflight_audit.json')['passed']
    assert not (TRIAL/'cases').exists()
    identities=dict(previous['identities'])
    paths=[p for p in (TRIAL/'preflight').rglob('*') if p.is_file()]
    paths+=[TRIAL/n for n in ('manifest.json','preflight_result.json','preflight_audit.json')]
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'execution_manifest.json',dict(identities=identities,max_physical_attempts=1,
        model_calls=0,training_updates=0))
