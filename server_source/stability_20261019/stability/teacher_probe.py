"""仅使用训练任务比较参数语义提示；所有真实输出保留。"""
import json
from pathlib import Path
import urllib.request
from training.refine.prompt import build_messages, parse_response
from reflection.reflector import Parameters
from stability.teacher import ENDPOINT
from stability.experiment import OUT

SEMANTICS = '''\n补充执行器的实际语义：time_scale只改变执行时间，空间路径不变。
grasp_offset只平移抓取位置；place_offset只平移释放位置，二者不是同一个位置。
lift_height改变抓起之后、横向搬运之前的竖直抬升距离。
reground和replan在当前仿真中不自动改变空间路径，不生成新的候选。
先确定报告的失败阶段，再核对所选参数能否影响该阶段的失败机制。
接触包围盒的lower_xyz与upper_xyz分别是世界坐标下的下界与上界，Z是高度。'''


def main():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    rows = []
    root = Path('/home/yeliheng/grasp_server/improvement_20261019/parity')
    for index in (16, 24, 32, 136, 152):
        task = json.loads((root/f'{index:05d}'/'result.json').read_text())
        first = task['records'][0]
        for variant in ('v3', 'semantics'):
            messages = build_messages(task['instruction'], first['error'], parameters=first['parameters'])
            if variant == 'semantics':
                messages[0]['content'] += SEMANTICS
            request = urllib.request.Request(ENDPOINT+'/reflect',
                data=json.dumps({'messages': messages}, ensure_ascii=False).encode(),
                headers={'Content-Type': 'application/json'})
            with opener.open(request, timeout=240) as response:
                output = json.load(response)
            row = {'case': index, 'variant': variant, 'messages': messages, 'response': output}
            try:
                row['parsed'] = parse_response(output['text'], Parameters().updated(first['parameters'])).to_dict()
            except ValueError as error:
                row['error'] = str(error)
            rows.append(row)
            (OUT/'teacher-probe.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2))
            print(json.dumps({k: v for k, v in row.items() if k not in ('messages', 'response')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()

