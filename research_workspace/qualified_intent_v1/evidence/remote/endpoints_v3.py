from unittest.mock import patch
from qualified_intent_v1 import endpoints
from qualified_intent_v1.common import ROOT, save, sha
from qualified_intent_v1.model_v3 import OUTPUT, verified


def main():
    paths = [ROOT/'endpoints_v3.py', ROOT/'endpoints_v3.sbatch']
    identities = {str(p): sha(p) for p in paths}
    save(OUTPUT/'endpoint_entry.json', dict(identities=identities))
    with patch.object(endpoints, 'RUN', OUTPUT), patch.object(endpoints, 'verify', verified):
        endpoints.main()
    assert all(sha(p) == h for p, h in identities.items())


if __name__ == '__main__':
    main()
