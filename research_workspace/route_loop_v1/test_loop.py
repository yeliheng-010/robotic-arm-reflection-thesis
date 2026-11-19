"""覆盖配置动作和严格解析，避免配置被静默忽略。"""
import unittest
from reflection.reflector import Parameters
from loopstudy.actions import initial,validate,candidates,choose_rule
from loopstudy.selection import resolve


def feedback(phase):
    segment = 'transport' if phase=='carry_transport' else 'descent'
    return dict(error_type='collision',evidence={'motion_context':{'phase':phase},
        'diagnostics':{'motion_segment':segment,'available_candidate_count':5}})


class LoopTests(unittest.TestCase):
    def test_legacy_candidates_cannot_change_route(self):
        state=initial()
        rows=candidates(feedback('place_descent'),state,[],legacy=True)
        self.assertTrue(rows)
        self.assertTrue(all(r['state']['profile']=='original' for r in rows))

    def test_scene_identifiers_do_not_change_candidates(self):
        report=feedback('place_descent')
        expected=candidates(report,initial(),[])
        report.update(scene_id='hidden',seed=999999,future_success=True)
        self.assertEqual(expected,candidates(report,initial(),[]))

    def test_unknown_profile_is_rejected(self):
        state = initial()
        state['profile']='arbitrary'
        with self.assertRaises(ValueError):
            validate(state)

    def test_transport_then_descent_changes_correct_components(self):
        state = initial()
        report = feedback('carry_transport')
        row = choose_rule(candidates(report,state,[]),state,report=report)
        self.assertEqual(.45,row['state']['parameters']['lift_height'])
        self.assertEqual('original',row['state']['profile'])
        report = feedback('place_descent')
        new = choose_rule(candidates(report,row['state'],[]),row['state'],report=report)
        self.assertEqual('descent_minus45',new['state']['profile'])
        self.assertEqual(row['state']['parameters'],new['state']['parameters'])

    def test_tried_state_is_not_repeated(self):
        state = initial()
        state['parameters']['lift_height']=.45
        report = feedback('place_descent')
        rows = candidates(report,state,[])
        chosen = choose_rule(rows,state,report=report)
        history=[dict(selected=chosen)]
        self.assertNotIn(chosen['id'],[r['id'] for r in candidates(report,state,history)])

    def test_strict_id_parser(self):
        rows = candidates(feedback('place_descent'),initial(),[])
        value=resolve('{"action_id":"'+rows[0]['id']+'"}',rows)
        self.assertEqual(rows[0],value)
        for text in ('{"action_id":"unknown"}','{"action_id":"x","action_id":"y"}',
                     '{"action_id":"x","changes":{}}','[]'):
            with self.assertRaises(ValueError):
                resolve(text,rows)

    def test_candidate_generation_is_deterministic_and_does_not_mutate_state(self):
        state = initial()
        first = candidates(feedback('place_descent'),state,[])
        self.assertEqual(first,candidates(feedback('place_descent'),state,[]))
        self.assertEqual(initial(),state)
        self.assertTrue(all(validate(r['state'])==r['state'] for r in first))


if __name__=='__main__':
    unittest.main()
