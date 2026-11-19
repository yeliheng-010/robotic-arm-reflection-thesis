from pathlib import Path
from qualified_closure_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'


def freeze():
    from qualified_closure_v1.common import verify as verify_prior
    prior = verify_prior()
    sources = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    result = dict(sources=sources, originals={**prior['originals'], **prior['sources']},
                  physical_budget=0, model_budget=0, training_budget=0)
    save(RUN / 'manifest.json', result)
    return result


def verify():
    result = read(RUN / 'manifest.json')
    for section in ('originals', 'sources'):
        for name, digest in result[section].items():
            assert sha(name) == digest, name
    return result
