import sys
from unittest.mock import patch
from reflection.__main__ import bootstrap
bootstrap()
import camera_probe
from camera_registration import configuration
from common import ROOT, PARENT, read, save, sha, verify

OUTPUT = ROOT/'camera_v2'


def prepare():
    assert not OUTPUT.exists()
    prior = verify(ROOT/'manifest.json')
    fresh = verify(PARENT/'fresh_accuracy_v1/run/manifest.json')
    rows = []
    for spec in prior['rows']:
        fixed = dict(spec)
        if 'selection' in spec:
            seed = int(spec['name'].split('_')[-1])
            fixed['config'] = configuration(fresh['cases'],seed)
            assert fixed['config']['camera']==read(spec['selection'])['attempts'][0]['camera']
        rows.append(fixed)
    identities = dict(prior['identities'])
    paths = [p for p in ROOT.iterdir() if p.suffix in ('.py','.sh','.sbatch')]
    identities.update({str(p):sha(p) for p in paths})
    save(OUTPUT/'manifest.json',dict(rows=rows,identities=identities,
        physical_attempts=0,model_calls=0,training_updates=0,max_new_cameras_per_state=128))


def run(mode):
    rows = verify(OUTPUT/'manifest.json')['rows']
    with patch.object(camera_probe,'ROOT',OUTPUT):
        for spec in rows:
            camera_probe.run(spec,mode)


if __name__=='__main__':
    prepare() if sys.argv[1]=='prepare' else run(sys.argv[1])
