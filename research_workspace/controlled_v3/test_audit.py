"""真实失败回归与双轮历史测试；不调用模型、不修改历史证据。"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from reflection.errors import ErrorReport, ErrorType
from reflection.reflector import Parameters
from flashnext.client import MODEL
from controlled.audit import audit_case, audit_feedback, audit_request
from controlled.client import ControlledFlash
from controlled.config import MAX_TOKENS, tasks, scenario
from controlled.feedback import ProjectedReflector, project_report

ARCHIVE = Path('/home/yeliheng/grasp_server/controlled_v2/smoke')


class AuditRegressionTests(unittest.TestCase):
    def setUp(self):
        directory = ARCHIVE/'tasks/18/flash'
        self.result = json.loads((directory/'result.json').read_text())
        self.event = json.loads((directory/'requests.jsonl').read_text().splitlines()[0])
        self.record = self.result['records'][0]
        self.projected = project_report(self.record['error'], self.result['scenario'], attempt=1)

    def check_event(self, event):
        audit_request(event, self.result, record=self.record, projected=self.projected, history=[])

    def test_real_failed_audit_replays_all_three_arms(self):
        result = audit_case(ARCHIVE, 18, tasks()[18])
        self.assertTrue(result['passed'])
        self.assertEqual({'retry': 0, 'rule': 1, 'flash': 1}, result['calls'])

    def test_changed_payload_fields_remain_rejected(self):
        self.check_event(self.event)
        changes = (
            ('residual', lambda p: p['error']['evidence']['placement_residual_xy'].__setitem__(0, 0)),
            ('parameter', lambda p: p['parameters'].__setitem__('lift_height', .48)),
            ('history', lambda p: p.__setitem__('history', [{'error': 'invented'}])),
            ('missing_evidence', lambda p: p['error']['evidence'].pop('placement_residual_xy')),
        )
        for name, mutate in changes:
            with self.subTest(name=name):
                event = copy.deepcopy(self.event)
                payload = json.loads(event['request']['messages'][1]['content'])
                mutate(payload)
                event['request']['messages'][1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
                with self.assertRaises(AssertionError):
                    self.check_event(event)

    def test_role_system_and_budget_changes_remain_rejected(self):
        self.check_event(self.event)
        changes = (
            lambda e: e['request']['messages'][0].__setitem__('role', 'user'),
            lambda e: e['request']['messages'][0].__setitem__('content', 'changed system'),
            lambda e: e['request'].__setitem__('max_tokens', MAX_TOKENS+1),
        )
        for mutate in changes:
            event = copy.deepcopy(self.event)
            mutate(event)
            with self.assertRaises(AssertionError):
                self.check_event(event)

    def test_two_turn_history_preserves_observed_projection(self):
        config = scenario(82000, 'feedback')
        report = ErrorReport(ErrorType.EMPTY_GRASP, 'raw', {
            'grasp_residual_xy': [.04, .02], 'diagnostics': {'available_candidate_count': 5}})
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            reflector = ProjectedReflector(ControlledFlash('test', directory), config, directory=directory)
            records, parameters = [], Parameters()
            for attempt, height in enumerate((.45, .48), 1):
                response_text = json.dumps({'cause': 'test', 'changes': {'lift_height': height}})
                def generate(prompt, *, max_tokens):
                    return dict(request={'messages': prompt, 'max_tokens': max_tokens}, text=response_text,
                                response={'model': MODEL, 'choices': [{'finish_reason': 'stop',
                                          'message': {'content': response_text}}]})
                with patch('controlled.client.generate', side_effect=generate):
                    answer = reflector.reflect(report, parameters)
                records.append(dict(attempt=attempt, error=report.to_dict(), parameters=parameters.to_dict(),
                                    reflection=answer.to_dict()))
                parameters = parameters.updated(answer.changes)
            result = dict(instruction='test', records=records, scenario=config)
            self.assertEqual(2, audit_feedback(directory, result, arm='flash'))
            events = (directory/'requests.jsonl').read_text().splitlines()
            second = json.loads(events[1])
            payload = json.loads(second['request']['messages'][1]['content'])
            self.assertEqual(1, len(payload['history']))
            payload['history'][0]['reflection']['changes']['lift_height'] = .47
            second['request']['messages'][1]['content'] = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
            (directory/'requests.jsonl').write_text(events[0]+'\n'+json.dumps(second)+'\n')
            with self.assertRaises(AssertionError):
                audit_feedback(directory, result, arm='flash')


if __name__ == '__main__':
    unittest.main()
