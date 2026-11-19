import sys
from model_grasp_intent_v1.model import parse
from qualified_feedback_v1.common import RUN, read, save, sha, verify


def main(ordinal):
    verify()
    folder = RUN/f'decision_{ordinal}'
    request = read(folder/'request.json')
    save(folder/'call_started.json', dict(request_sha256=sha(folder/'request.json')))
    from mm_generator import VisualGenerator
    generator = VisualGenerator()
    assert generator.identity['adapter_enabled'] is False
    values, encoding = generator.prepare_images(request['messages'], [request['image']])
    save(folder/'encoding.json', dict(encoding=encoding, identity=generator.identity))
    response = generator.generate(values)
    save(folder/'response.json', response)
    try:
        result = dict(valid=True, action=parse(response)['action'])
    except (ValueError, TypeError, KeyError) as error:
        result = dict(valid=False, action=None, error=str(error))
    save(folder/'validated.json', result)
    print(result, flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))
