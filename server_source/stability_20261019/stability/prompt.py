"""完整诊断留档，教师仅接收紧凑测量摘要；不提供规则答案。"""
import copy
import json
from training.refine.prompt import build_messages as original_messages, parse_response

FORMAT = 'text-reflection-v4-compact-evidence'


def project_error(report):
    value = copy.deepcopy({k: v for k, v in report.items() if k not in ('timestamp', 'image_paths')})
    evidence = value.get('evidence', {})
    geometry = evidence.pop('contact_geometry', None)
    if geometry is not None:
        environments = {pair[1] for pair in evidence.get('contacts', [])}
        relevant = [row for row in geometry if environments.intersection(row.get('bodies', []))]
        evidence['contact_details'] = relevant[:4]
        evidence['contact_detail_count'] = len(relevant)
    filtering = evidence.get('diagnostics', {}).get('grasp_filter', {})
    ious = filtering.pop('collision_iou', None)
    if ious:
        filtering['iou_summary'] = {'count': len(ious), 'min': min(ious), 'max': max(ious)}
    return value


def build_messages(instruction, report, *, parameters, history=()):
    previous = [{**item, 'error': project_error(item['error'])} for item in history]
    messages = original_messages(instruction, project_error(report), parameters=parameters, history=previous)
    messages[1]['content'] = json.dumps(json.loads(messages[1]['content']),
                                       ensure_ascii=False, separators=(',', ':'))
    return messages

