"""旧/新反馈的事实读取检查；不将字段抽取称为闭环恢复。"""
import copy
import json
import os
from pathlib import Path
import random
import sys

ROOT = Path('/home/yeliheng/grasp_server/feedback_semantics_v2')
sys.path.insert(0,str(ROOT))
from semanticfix2.protocol import verify,sha
from semanticfix2.context import enrich,project,PHASES
from controlled.feedback import project_report
from flashnext.client import generate,append,ready
from bounded.selection import unique_object
from stability.collection_status import atomic

REPEATS = 2
ORDER_SEED = 906500
MAX_TOKENS = 256
BASE_PROMPT = '''你读取机械臂失败反馈，只回答证据支持的事实。输出严格JSON，且只有两个字段：
phase: 把动作阶段归入 grasp_prepare, grasp_approach, grasp_pose, carry_lift, carry_transport,
place_descent, post_release_retract, return_home 或 unknown。
contacting_bodies: 实际接触障碍的机器人连杆或被搬运物体名称列表，不包括障碍物SafetyDivider。
不能把根节点/类别名称猜成实际接触部位；证据没有实际部位时返回空列表。不输出解释或动作。'''
NEW_GUIDANCE = '''
action=move_to_point的lift/transport/descent分别是抓取后的抬升、携物运输、放置下降；
action=move_to_grasp_pose的pregrasp/approach/grasp属于抓取过程。
motion_context给出执行器的阶段定义；contact_details.contacts[].geometries[].body才是实际接触部位，
root仅表示归类根节点，不能用root替代body。'''


def fixtures():
    rows = []
    for item in verify()['items']:
        if item['variant'] not in ('default','lift45'):
            continue
        path = ROOT/'physical/tasks'/item['id']/'result.json'
        result = json.loads(path.read_text())
        summary = json.loads((path.parent/'summary.json').read_text())
        assert summary['audit']['passed']
        report = result['records'][0]['error']
        rows.append(dict(id=item['id'],report=report,config=result['scenario'],source_sha256=sha(path),synthetic=False))
        if item['variant']=='default':
            value = copy.deepcopy(report)
            value['evidence']['diagnostics'].update(action='move_to_grasp_pose',motion_segment='approach')
            value = enrich(value,attempt=1)
            rows.append(dict(id=item['id']+'_synthetic_approach',report=value,config=result['scenario'],
                             source_sha256=sha(path),synthetic=True))
    return rows


def request_messages(fixture,arm):
    report = fixture['report']
    shown = project(report,fixture['config'],attempt=1) if arm=='explicit' else project_report(report,fixture['config'],attempt=1)
    return [{'role':'system','content':BASE_PROMPT+(NEW_GUIDANCE if arm=='explicit' else '')},
            {'role':'user','content':json.dumps(shown,ensure_ascii=False)}]


def expected(fixture):
    evidence = fixture['report']['evidence']
    phase = evidence['motion_context']['phase']
    bodies = sorted({g['body'] for c in evidence['contact_details']['contacts']
                     for g in c['geometries'] if g['body']!='SafetyDivider'})
    return dict(phase=phase,contacting_bodies=bodies)


def evaluate(event,fixture,arm):
    row = dict(valid=False,phase_correct=False,bodies_supported=False,detail_complete=False)
    try:
        value = json.loads(event['text'],object_pairs_hook=unique_object)
        assert set(value)=={'phase','contacting_bodies'} and isinstance(value['phase'],str)
        assert value['phase'] in {p[0] for p in PHASES.values()}|{'unknown'}
        assert isinstance(value['contacting_bodies'],list) and all(isinstance(x,str) for x in value['contacting_bodies'])
        assert len(value['contacting_bodies'])==len(set(value['contacting_bodies']))
        target = expected(fixture)
        body_correct = sorted(value['contacting_bodies'])==target['contacting_bodies']
        row.update(valid=True,parsed=value,phase_correct=value['phase']==target['phase'],
                   bodies_supported=body_correct if arm=='explicit' else value['contacting_bodies']==[],
                   detail_complete=body_correct)
    except (ValueError,KeyError,TypeError,AssertionError) as error:
        row['validation_error'] = repr(error)
    return row


def run():
    assert os.environ.get('SLURM_JOB_ID')
    values = fixtures()
    assert len(values)==6
    output = ROOT/'semantic'
    output.mkdir(exist_ok=False)
    order = [(i,a,r) for i in range(len(values)) for a in ('legacy','explicit') for r in range(REPEATS)]
    random.Random(ORDER_SEED).shuffle(order)
    protocol = dict(fixtures=values,order=order,code_sha256=sha(Path(__file__)),
                    physical_protocol_sha256=sha(ROOT/'protocol.json'),max_tokens=MAX_TOKENS)
    atomic(output/'protocol.json',protocol)
    status = dict(status='running',expected=len(order),completed=0,rows=[],models=ready(),job=os.environ['SLURM_JOB_ID'])
    try:
        for index,arm,repeat in order:
            fixture = values[index]
            event = generate(request_messages(fixture,arm),max_tokens=MAX_TOKENS)
            event.update(id=f"{fixture['id']}/{arm}/{repeat}",fixture=index,arm=arm,repeat=repeat)
            event['score'] = evaluate(event,fixture,arm)
            append(output/'requests.jsonl',event)
            status['rows'].append(event)
            status['completed'] += 1
            atomic(output/'progress.json',{k:v for k,v in status.items() if k not in ('rows','models')})
            assert not event.get('service_error'), 'Service error'
        assert protocol['code_sha256']==sha(Path(__file__))
        verify()
        status['status'] = 'completed'
    except BaseException as error:
        status.update(status='failed',error=repr(error))
        raise
    finally:
        atomic(output/'result.json',status)
        atomic(output/'progress.json',{k:v for k,v in status.items() if k not in ('rows','models')})


if __name__=='__main__':
    run()
