"""避免把当前执行器能力反向声称为历史动作全部已检查。"""
from visual_requests import build as original
from prompts import messages


def build(branch,session,view):
    bundle=original(branch,session,view)
    request=bundle['request']
    request['execution_semantics']['fixed_executor']='Requested actions cannot bypass the configured executor safety checks.'
    bundle['direct_messages']=messages(request,mode='direct')
    bundle['diagnostic_messages']=messages(request,mode='diagnostic')
    return bundle
