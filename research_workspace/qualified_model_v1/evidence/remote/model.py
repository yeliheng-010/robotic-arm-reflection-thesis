from qualified_model_v1.common import RUN, read, save, sha, verify
from qualified_model_v1.policy import parse


def run(generator, entry):
    folder = RUN/str(entry['seed'])
    request = read(entry['request'])
    assert sha(request['image']) == request['image_sha256']
    save(folder/'call_started.json', dict(request_sha256=sha(entry['request'])))
    values, encoding = generator.prepare_images(request['messages'], [request['image']])
    save(folder/'encoding.json', dict(encoding=encoding, identity=generator.identity))
    response = generator.generate(values)
    save(folder/'response.json', response)
    try:
        result = dict(valid=True, parsed=parse(response))
    except (ValueError, TypeError, KeyError) as error:
        result = dict(valid=False, error=str(error), parsed=None)
    save(folder/'validated.json', result)
    print(dict(seed=entry['seed'], **result, tokens=response['completion_tokens']), flush=True)


def main():
    manifest = verify()
    from mm_generator import VisualGenerator
    generator = VisualGenerator()
    assert generator.identity['adapter_enabled'] is False
    for entry in manifest['entries']:
        run(generator, entry)
    verify()


if __name__ == '__main__':
    main()
