from pathlib import Path
from surface_grasp_v1.common import read,save,sha

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent
TRIAL=ROOT/'trial'
STATIC=PROJECT/'surface_grasp_v1'
SOURCE=PROJECT/'qualification_strategy_v1/actual/cases/F1_964347_varied_noisy'


def verify(path):
    value=read(path)
    for name,digest in value['identities'].items():
        assert sha(name)==digest,name
    return value


def entry():
    return verify(TRIAL/'manifest.json')['entry']


def selected():
    result=read(STATIC/'paths/audit/result.json')
    name=next(row['candidate'] for row in result['checked'] if row['result']['status']=='ready')
    return next(row for row in read(STATIC/'catalogue.json') if row['id']==name)


def frozen_plan():
    return read(STATIC/'paths/audit'/selected()['id']/'private_plan.json')
