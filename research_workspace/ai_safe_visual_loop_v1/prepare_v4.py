from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import prepare_v3
from qp_common import verify as previous
from sv_common import ROOT, read, sha

original_cases = prepare_v3.qualified_cases


def prerequisites():
    paths = [ROOT/'code_checks_v4/verification.json',
        ROOT.parent/'natural_top_pilot_v1/inventory.json', ROOT.parent/'ai_visual_service_v1/audit.json']
    checked, recovery, visual = [read(p) for p in paths]
    assert checked['passed'] and visual['passed'] and visual['model_calls'] == 4
    prepare_v3.validate_recovery(recovery)
    identities = dict(previous()['identities'])
    for value in (checked, recovery, visual):
        assert all(sha(p) == h for p,h in value['identities'].items())
        identities.update(value['identities'])
    pilot = read(ROOT.parent/'natural_top_pilot_v1/manifest.json')
    assert all(sha(p) == h for p,h in pilot['identities'].items())
    identities.update(pilot['identities'])
    identities.update({str(p):sha(p) for p in paths})
    return identities, checked


def qualified_cases(reserved, result):
    return [dict(case, strategy='original') for case in original_cases(reserved, result)]


if __name__ == '__main__':
    with patch.multiple(prepare_v3, prerequisites=prerequisites, qualified_cases=qualified_cases):
        prepare_v3.main()
