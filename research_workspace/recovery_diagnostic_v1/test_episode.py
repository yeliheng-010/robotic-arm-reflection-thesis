"""直接运行原episode循环，验证额外一次执行和成功即停。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from loopstudy import episode
from variant import configured


class EpisodeTests(unittest.TestCase):
    def execute(self,variant,success_at):
        seen=[]
        def attempt(item,state,*,directory,index):
            seen.append(index)
            return dict(index=index,state=state,success=index==success_at,feedback={})
        def decide(item,step,history):
            return dict(selected=dict(state=step['state']))
        with tempfile.TemporaryDirectory() as temporary:
            with configured(dict(variant=variant,max_attempts=4 if variant=='budget4' else 3)), \
                 patch.object(episode,'configuration',return_value={}), \
                 patch.object(episode,'attempt',attempt), patch.object(episode,'decide',decide):
                value=episode.run({},Path(temporary)/'task')
        return seen,value

    def test_fourth_attempt_is_executed(self):
        seen,value=self.execute('budget4',4)
        self.assertEqual([1,2,3,4],seen)
        self.assertTrue(value['success'])
        self.assertEqual(3,len(value['decisions']))

    def test_success_at_three_does_not_run_four(self):
        seen,value=self.execute('budget4',3)
        self.assertEqual([1,2,3],seen)
        self.assertTrue(value['success'])

    def test_missing_intervention_retains_three_limit(self):
        seen,value=self.execute('no_missing',4)
        self.assertEqual([1,2,3],seen)
        self.assertFalse(value['success'])


if __name__=='__main__':
    unittest.main()
