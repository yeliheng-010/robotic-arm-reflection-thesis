import time
from pathlib import Path
from prompts import messages
from f_common import save, sha

FIELDS = {'condition', 'mode', 'ordinal', 'request', 'messages', 'visual'}


def validate(body, server):
    assert set(body) == FIELDS and body['condition'] in server.conditions
    assert body['mode'] in ('direct', 'diagnostic')
    assert type(body['ordinal']) is int and 1 <= body['ordinal'] <= server.max_decisions
    assert body['messages'] == messages(body['request'], mode=body['mode'])
    visual = body['visual']
    assert set(visual) == {'paths', 'sha256', 'order'}
    assert visual['order'] == ['before', 'latest_after']
    assert len(visual['paths']) == len(visual['sha256']) == 2
    for name, digest in zip(visual['paths'], visual['sha256']):
        path = Path(name).resolve(strict=True)
        assert path.suffix == '.png' and any(path.is_relative_to(root) for root in server.image_roots)
        assert sha(path) == digest
    return f"{body['condition']}_{body['mode']}_{body['ordinal']}"


def execute(server, body):
    key = validate(body, server)
    assert server.calls < server.max_calls
    target = server.root/'service/requests'
    save(target/f'{key}_request.json', body)
    server.calls += 1
    started = time.monotonic()
    try:
        values, encoding = server.generator.prepare_images(body['messages'], body['visual']['paths'])
        save(target/f'{key}_generation_started.json', dict(encoding=encoding))
        response = server.generator.generate(values)
    except BaseException as error:
        save(target/f'{key}_error.json', dict(error=repr(error), reserved_calls=1))
        raise
    result = dict(id=key, response=response, encoding=encoding,
        manifest_sha256=sha(server.root/'manifest.json'), elapsed_s=time.monotonic()-started)
    save(target/f'{key}_response.json', result)
    return result
