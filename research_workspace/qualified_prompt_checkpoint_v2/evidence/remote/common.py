from pathlib import Path
from qualified_prompt_checkpoint_v1 import protocol as original
from qualified_prompt_checkpoint_v1.protocol import read, save, sha, classify

ROOT = Path(__file__).resolve().parent
PROJECT, RUN = ROOT.parent, ROOT / 'run'
PRIOR = PROJECT / 'qualified_prompt_checkpoint_v1'


def prior_zero_generation():
    result = read(PRIOR / 'run/failure_audit.json')
    assert result['passed'] and result['model_calls'] == result['generations_started'] == 0
    assert read(PRIOR / 'run/model_claim.json')['consumed'] == 1
    assert all(not (PRIOR / 'run' / name).exists() for name in
               ('generation_started.json', 'response.json', 'result.json'))
    return result


def verify():
    prior_zero_generation()
    return original.verify(RUN)


def reserve():
    prior_zero_generation()
    original.reserve(RUN)
