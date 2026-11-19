from qualified_execution_v1.common import ROOT, PROJECT, RUN, SEED, read, save, sha, verify


def prepare():
    old = PROJECT/'qualified_entry_v1/run'
    manifest = read(old/'audit_manifest_v2.json')
    identities = dict(manifest['identities'])
    assert all(sha(p) == h for p, h in identities.items())
    audit = read(old/'audit_result.json')
    assert audit['passed'] and audit['commands_identical']
    assert read(old/'result.json')['commands_passed']
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py', '.md', '.sbatch')]
    paths += [old/n for n in ('audit_result.json', 'result.json', 'commands.json', 'audit_manifest_v2.json')]
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'manifest.json', dict(identities=identities, seed=SEED, max_physical_attempts=1,
        model_calls=0, training_runs=0, online_model_decisions=False,
        observation_policy='Qualified initial input; no held-phase image consumed; final publication independently qualified',
        scope='One model-selected frozen plan with original safety stops; not autonomous online recovery',
        prior_predicted_held_rejection_preserved=True))


def authorize():
    manifest = verify()
    assert read(RUN/'preflight/result.json')['passed']
    assert read(RUN/'preflight_audit.json')['passed']
    paths = [p for p in (RUN/'preflight').rglob('*') if p.is_file()]
    paths += [RUN/'preflight_audit.json', RUN/'manifest.json']
    identities = dict(manifest['identities'])
    identities.update({str(p): sha(p) for p in paths})
    save(RUN/'execution_manifest.json', dict(identities=identities, max_physical_attempts=1,
        max_model_calls=0, max_training_runs=0))


def claim():
    verify()
    manifest = read(RUN/'execution_manifest.json')
    assert manifest['max_physical_attempts'] == 1
    assert all(sha(p) == h for p, h in manifest['identities'].items())
    assert not (RUN/'physical').exists()
    save(RUN/'attempt_claim.json', dict(consumed=1, execution_manifest_sha256=sha(RUN/'execution_manifest.json')))


if __name__ == '__main__':
    import sys
    {'prepare': prepare, 'authorize': authorize}[sys.argv[1]]()
