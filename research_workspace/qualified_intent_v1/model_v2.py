import sys
from unittest.mock import patch
from qualified_intent_v1 import model
from qualified_intent_v1.compact import compact
from qualified_intent_v1.common import ROOT, RUN, read, save, sha, verify

OUTPUT = ROOT/'run_v2'


def prepare():
    previous = verify()
    entries, identities = [], dict(previous['identities'])
    for entry in previous['entries']:
        seed = entry['seed']
        request, rounding = compact(read(entry['request']))
        save(OUTPUT/f'{seed}/request.json', request)
        save(OUTPUT/f'{seed}/rounding.json', rounding)
        entries.append(dict(entry, request=str(OUTPUT/f'{seed}/request.json')))
    paths = [ROOT/n for n in ('compact.py', 'model_v2.py', 'run_v2.sbatch')]
    paths.extend(p for p in OUTPUT.rglob('*.json'))
    identities.update({str(p): sha(p) for p in paths})
    save(OUTPUT/'manifest.json', dict(previous, entries=entries, identities=identities,
        predecessor='run: input token gate rejected first preparation before any generate call',
        full_precision_inputs=str(RUN), max_model_calls=2))


def verified():
    value = read(OUTPUT/'manifest.json')
    assert all(sha(p) == h for p, h in value['identities'].items())
    return value


def run():
    with patch.object(model, 'RUN', OUTPUT), patch.object(model, 'verify', verified):
        model.main()


if __name__ == '__main__':
    {'prepare': prepare, 'run': run}[sys.argv[1]]()
