from pathlib import Path
from qualified_model_v1.common import read, save, sha

ROOT = Path(__file__).resolve().parent
RUN = ROOT / 'run'
OLD = ROOT.parent / 'qualified_execution_v1'


def freeze():
    from qualified_execution_v1.closeout import verify_inputs
    prior = verify_inputs()
    originals = {str(p): sha(p) for p in OLD.rglob('*')
                 if p.is_file() and p.suffix in ('.py', '.sbatch', '.json', '.npz', '.md')}
    sources = {str(p): sha(p) for p in ROOT.iterdir() if p.suffix in ('.py', '.sbatch', '.md')}
    result = dict(prior=prior, originals=originals, sources=sources,
                  physical_budget=0, model_budget=0, training_budget=0)
    save(RUN / 'manifest.json', result)
    return result


def verify():
    result = read(RUN / 'manifest.json')
    for section in ('originals', 'sources'):
        for name, digest in result[section].items():
            assert sha(name) == digest, name
    return result
