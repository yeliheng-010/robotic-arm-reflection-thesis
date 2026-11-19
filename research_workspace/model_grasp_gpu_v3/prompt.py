from model_grasp_gpu_v2.pack import pack as compact
from model_grasp_intent_v1.requests import messages as original_messages
from model_grasp_intent_v1.contract import CHOICES


def pack(request):
    result = compact(request)
    for action in result['actions']:
        if action['id'] == 'PROPOSE_GRASP':
            properties = {key:dict(type='string' if key=='region' else 'integer',enum=list(values))
                          for key,values in CHOICES.items()}
            action['args_spec'] = dict(type='object',properties=properties,
                                      required=list(CHOICES),additionalProperties=False)
    return result


def messages(request):
    result = original_messages(request)
    result[0]['content'] += ('\nactions中args_spec是参数的JSON Schema，不是应当原样输出的args。'
        '每个字段只选一个enum里的标量值；region是字符串，其余参数是整数。'
        '不得复制整个枚举列表，不得输出数组、type、enum或properties。'
        '按当前图像和观测自主选择值；若不提出抓取则选择合法的STOP。')
    return result
