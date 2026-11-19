import json

SYSTEM = '''你是机械臂的视觉定位模块。只根据给出的场景图像和自然语言任务自主定位，
不要假定已知物体坐标。输出严格JSON，不要Markdown或说明：
{"action":"LOCATE","source_pixel":[u,v],"destination_pixel":[u,v]}
像素使用0到1000的归一化整数坐标，左上角[0,0]、右下角[1000,1000]。
source_pixel选在待抓物体清晰可见的实体表面内部；destination_pixel选在目标容器内部。
如果不能可靠辨认任一对象，输出{"action":"STOP"}。本步骤不执行运动。'''


def parse(response):
    if response['finish_reason'] != 'stop':
        raise ValueError('Incomplete generation')
    value = json.loads(response['text'])
    if value == {'action': 'STOP'}:
        return value
    if set(value) != {'action', 'source_pixel', 'destination_pixel'} or value['action'] != 'LOCATE':
        raise ValueError('Unexpected response fields')
    for name in ('source_pixel', 'destination_pixel'):
        pixel = value[name]
        if type(pixel) is not list or len(pixel) != 2:
            raise ValueError('Invalid pixel shape')
        if not all(type(v) is int and 0 <= v <= 1000 for v in pixel):
            raise ValueError('Invalid normalized coordinate')
    return value


def pixel(values, *, width, height):
    return [round(values[0]*(width-1)/1000), round(values[1]*(height-1)/1000)]
