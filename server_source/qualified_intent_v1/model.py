from model_grasp_intent_v1.model import parse
from qualified_intent_v1.common import RUN, read, save, sha, verify


def main():
    manifest = verify()
    from mm_generator import VisualGenerator
    generator = VisualGenerator()
    assert not generator.identity['adapter_enabled']
    for entry in manifest['entries']:
        folder = RUN/str(entry['seed'])
        request = read(entry['request'])
        assert sha(request['image']) == entry['image_sha256']
        save(folder/'call_started.json', dict(request_sha256=sha(entry['request'])))
        values, encoding = generator.prepare_images(request['messages'], [request['image']])
        save(folder/'encoding.json', dict(encoding=encoding, identity=generator.identity))
        response = generator.generate(values)
        save(folder/'response.json', response)
        try:
            action = parse(response)['action']
            assert action['id'] in ('PROPOSE_GRASP', 'STOP')
            result = dict(valid=True, action=action)
        except (ValueError, TypeError, KeyError, AssertionError) as error:
            result = dict(valid=False, action=None, error=str(error))
        save(folder/'validated.json', result)
        print(dict(seed=entry['seed'], **result), flush=True)
    verify()


if __name__ == '__main__':
    main()
