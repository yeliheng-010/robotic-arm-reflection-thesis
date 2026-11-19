"""防止评估污染、组别错配，以及把失败任务从分母剔除。"""
import unittest
from stability.collection_plan import HELDOUT, task_plan
from stability.loop_protocol import plan, validate_call, validate_reply, summarize
from stability.parallel_state import topology, lane_indices


class LoopTests(unittest.TestCase):
    def test_new_cases_exclude_training_and_sealed_test_groups(self):
        cases = plan()
        self.assertEqual(6, len(cases))
        old = {(t['source'], t['destination'], t['fault'], t['seed']) for t in task_plan('batch')}
        for task in cases:
            self.assertEqual('validation', HELDOUT[(task['source'], task['destination'])])
            self.assertNotIn(tuple(task[k] for k in ('source', 'destination', 'fault', 'seed')), old)
        self.assertEqual({'calibration', 'collision', 'placement'}, {t['fault'] for t in cases})

    def test_inference_rejects_unknown_arm_and_assistant_answer_in_prompt(self):
        messages = [{'role': 'system', 'content': 'rules'}, {'role': 'user', 'content': 'evidence'}]
        self.assertEqual(('adapted', messages), validate_call(dict(arm='adapted', messages=messages)))
        with self.assertRaises(ValueError):
            validate_call(dict(arm='rule', messages=messages))
        with self.assertRaises(ValueError):
            validate_call(dict(arm='base', messages=messages+[{'role': 'assistant', 'content': 'answer'}]))

    def test_reply_cannot_silently_switch_model_arm(self):
        with self.assertRaises(ValueError):
            validate_reply(dict(arm='base', text='{}'), 'adapted')

    def test_invalid_task_stays_in_success_and_attempt_denominators(self):
        rows = [dict(arm='adapted', success=True, attempts=2, calls=1, invalid=0, service_errors=0),
                dict(arm='adapted', success=False, attempts=1, calls=1, invalid=1, service_errors=0)]
        result = summarize(rows).get('adapted', {})
        self.assertEqual(2, result.get('tasks'))
        self.assertEqual(.5, result.get('success_rate'))
        self.assertEqual(1.5, result.get('mean_attempts'))
        self.assertEqual(.5, result.get('invalid_output_rate'))

    def test_single_gpu_resume_assigns_all_unfinished_indices(self):
        try:
            types = topology(1)
        except ValueError:
            types = []
        self.assertEqual(['v100'], types)
        self.assertEqual([1, 3, 4], lane_indices(5, lane=0, lanes=1, completed={0, 2}))


if __name__ == '__main__':
    unittest.main()
