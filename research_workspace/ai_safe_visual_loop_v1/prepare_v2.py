from unittest.mock import patch
import prepare
from sv_common import ROOT, read, sha

original = prepare.prerequisites


def prerequisites():
    identities, checked = original()
    path = ROOT/'code_checks_v2/verification.json'
    revision = read(path)
    assert revision['passed'] and all(sha(p) == h for p,h in revision['identities'].items())
    identities.update(revision['identities'])
    identities[str(path)] = sha(path)
    return identities, dict(checked, tests=revision['tests'])


if __name__ == '__main__':
    with patch.object(prepare, 'prerequisites', prerequisites):
        prepare.main()
