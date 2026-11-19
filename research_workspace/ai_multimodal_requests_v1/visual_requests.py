"""真实RGB、公开执行事实与编码器偏差；不引入根因或后续动作结果。"""
from pathlib import Path
from nc_requests import build as text_bundle
from public_execution import public
from tracking_facts import summarize
from prompts import messages
from f_common import read,sha


def build(branch,session,view):
    bundle=text_bundle(branch,session,view)
    request=bundle['request']
    telemetry=next(r for r in request['evidence'] if r['field']=='robot_telemetry')
    telemetry.update(field='robot_tracking_summary',value=summarize(session.recorder.rows),
                     source='simulated_joint_encoders_and_executor_commands')
    facts=public(session.step,read(session.folder/'bridge.json'))
    request['evidence'].append(dict(id=f"e{len(request['evidence'])+1}",field='execution_facts',
        value=facts,source='command_runtime_and_task_evaluator'))
    before=session.folder/'execution/attempt_1/before.png'
    after=Path(view.paths[-1])/'rgb.png'
    assert before.is_file() and after.is_file()
    assert sha(after)==view.sampler.private[-1]['rgb_sha256']
    request['evidence'].append(dict(id=f"e{len(request['evidence'])+1}",field='attached_rgb_images',
        value=['before_current_attempt','latest_paused_observation'],source='unaltered_saved_camera_frames'))
    request['version']='safe-natural-multimodal-v1'
    request['sensing_status'].update(rgb='attached_before_and_latest_paused_frame',
        telemetry='attached_command_encoder_difference_summary')
    request['execution_semantics']['fixed_executor']='All attempts retain full path, self-collision and hardware joint-limit checks.'
    return dict(request=request,visual=dict(paths=[str(before),str(after)],
        sha256=[sha(before),sha(after)],order=['before','latest_after']),
        direct_messages=messages(request,mode='direct'),diagnostic_messages=messages(request,mode='diagnostic'))
