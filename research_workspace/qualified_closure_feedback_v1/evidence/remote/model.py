"""单次冻结请求的Qwen生成；准备与真实生成分别记账。"""
import sys
from model_grasp_intent_v1.model import parse
from qualified_closure_feedback_v1.common import RUN, read, save, sha, verify


def main(ordinal):
    verify()
    folder = RUN / f'decision_{ordinal}'
    claim = read(folder / 'model_claim.json')
    assert claim['ordinal'] == ordinal and claim['consumed'] == 1
    assert claim['request_sha256'] == sha(folder / 'request.json')
    save(folder / 'call_started.json', dict(request_sha256=claim['request_sha256']))
    request = read(folder / 'request.json')
    from mm_generator import VisualGenerator
    generator = VisualGenerator()
    assert generator.identity['adapter_enabled'] is False
    values, encoding = generator.prepare_images(request['messages'], [request['image']])
    save(folder / 'encoding.json', dict(encoding=encoding, identity=generator.identity))
    save(folder / 'generation_started.json', dict(reserved_ordinal=ordinal))
    response = generator.generate(values)
    save(folder / 'response.json', response)
    try:
        parsed = dict(valid=True, action=parse(response)['action'])
    except (ValueError, TypeError, KeyError) as error:
        parsed = dict(valid=False, action=None, error=str(error))
    save(folder / 'validated.json', parsed)
    print(parsed, flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))
