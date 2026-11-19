"""每个登记序号只调用一次真实基础模型，原始输出先落盘。"""
import sys
from model_grasp_gpu_v1.common import ROOT, SOURCE, BUDGET, read, save, sha, verify
from model_grasp_intent_v1.model import parse
from model_grasp_intent_v1.requests import messages


def main(ordinal):
    verify()
    assert 1 <= ordinal <= BUDGET['decisions']
    folder = ROOT/'run'/f'decision_{ordinal}'
    request = read(folder/'request.json')
    preflight = read(ROOT/'preflight.json')
    image = SOURCE/'execution/attempt_1/before.png'
    assert sha(image) == preflight['image_sha256']
    save(folder/'call_started.json', dict(ordinal=ordinal, image_sha256=sha(image)))
    from mm_generator import VisualGenerator
    generator = VisualGenerator()
    assert generator.identity['adapter_enabled'] is False
    prompt = messages(request)
    save(folder/'messages.json', prompt)
    values, encoding = generator.prepare_images(prompt, [str(image)])
    save(folder/'generation_started.json', dict(encoding=encoding, identity=generator.identity))
    response = generator.generate(values)
    save(folder/'raw_response.json', response)
    save(folder/'validated_response.json', parse(response))
    print(dict(ordinal=ordinal, valid=True, tokens=response['completion_tokens']), flush=True)


if __name__ == '__main__':
    main(int(sys.argv[1]))
