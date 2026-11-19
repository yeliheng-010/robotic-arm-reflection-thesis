"""只登记固定几何拒绝条件，原策略独立审计结果直接复用。"""
from qs_common import ROOT, PARENT, SOURCE, RUN, NAMES, read, save, sha, verify


def main():
    assert not RUN.exists()
    previous = verify(SOURCE/'manifest.json')
    result = verify(SOURCE/'result.json')
    audited = PARENT/'fresh_accuracy_v1/analysis/job_6408/result.json'
    audit = verify(audited)
    assert audit['passed']
    rows = [row for row in result['rows'] if row['status'] == 'geometry_rejected']
    assert {row['id'] for row in rows} == set(NAMES)
    cases, identities = [], dict(previous['identities'], **result['identities'])
    for row in rows:
        folder = SOURCE/'conditions'/row['id']/'original'
        case = verify(folder/'manifest.json')['cases'][0]
        qualification = folder/'qualification'/str(row['seed'])
        old = read(qualification/'result.json')
        reference = next(r for r in audit['geometry'] if r['id'] == row['id'])
        assert reference['replayed'] and reference['accepted'] is False and old['qualified'] is False
        cases.append(dict(case=case, qualification=str(qualification), old=old, audit=reference))
    files = [audited, SOURCE/'result.json', *ROOT.glob('*.py'), *ROOT.glob('*.sh'), *ROOT.glob('*.sbatch')]
    identities.update({str(p): sha(p) for p in files})
    save(RUN/'manifest.json', dict(cases=cases, identities=identities,
        max_top_planning_conditions=3, physical_attempts=0, model_calls=0, training_updates=0))
    print(dict(registered=len(cases), physical_attempts=0), flush=True)


if __name__ == '__main__':
    main()
