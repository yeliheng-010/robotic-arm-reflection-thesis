from held_observation_v1.common import ROOT,PROJECT,TRIAL,save,read,sha,verify,registered


def prepare():
    assert not TRIAL.exists()
    previous=verify(PROJECT/'surface_physical_v1/trial/execution_manifest.json')
    audited=verify(PROJECT/'surface_physical_audit_v2/audit.json')
    assert audited['passed'] and audited['success'] is False
    case=read(PROJECT/'surface_physical_v1/trial/manifest.json')['entry']['case']
    identities=dict(previous['identities'],**audited['identities'])
    paths=[p for p in ROOT.iterdir() if p.suffix in ('.py','.md','.sh','.sbatch')]
    paths+=[PROJECT/'surface_physical_audit_v2/audit.json']
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'manifest.json',dict(case=case,identities=identities,max_attempts=1,
        release_allowed=False,model_calls=0,training_runs=0,camera_budget_per_phase=32,
        physical_scope='Single observation-only attempt; stop before release'))


def execution():
    previous=registered()
    assert read(TRIAL/'preflight_result.json')['passed']
    assert read(TRIAL/'preflight_audit.json')['passed']
    identities=dict(previous['identities'])
    paths=[p for p in (TRIAL/'preflight').rglob('*') if p.is_file()]
    paths+=[TRIAL/'manifest.json',TRIAL/'preflight_result.json',TRIAL/'preflight_audit.json']
    identities.update({str(p):sha(p) for p in paths})
    save(TRIAL/'execution_manifest.json',dict(identities=identities,max_physical_attempts=1,
        release_allowed=False,model_calls=0,training_runs=0))
