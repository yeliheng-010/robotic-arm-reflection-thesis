"""仅认可实际EOS结束的严格JSON；不修复、重试或替模型选动作。"""
from decision import parse

MAX_TOKENS = 2048
MAX_INPUT_TOKENS = 16384
SEED = 42
MODES = ('direct', 'diagnostic')


def validate(response, request, *, mode):
    if response['finish_reason'] != 'stop':
        return dict(valid=False, error='Generation did not finish with EOS', parsed=None)
    try:
        value = parse(response['text'], request, mode=mode)
    except (ValueError, TypeError, KeyError) as error:
        return dict(valid=False, error=str(error), parsed=None)
    return dict(valid=True, error=None, parsed=value)


def finish(tokens, eos):
    if not tokens:
        raise ValueError('Empty generation')
    values = {eos} if isinstance(eos, int) else set(eos or [])
    if tokens[-1] in values:
        return 'stop'
    if len(tokens) >= MAX_TOKENS:
        return 'length'
    raise ValueError('Generation ended without configured EOS or token limit')
