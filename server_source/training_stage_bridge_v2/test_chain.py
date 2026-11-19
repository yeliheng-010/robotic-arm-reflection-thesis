import unittest
from pathlib import Path
from unittest.mock import patch
import watch


class ChainTests(unittest.TestCase):
    def test_only_v2_training_entry_with_both_prerequisites(self):
        value = dict(gate=dict(quantitative_ready=True), identities={}, outputs={})
        with patch.object(watch, 'read', return_value=value), patch.object(watch, 'sha', return_value='hash'), \
             patch.object(watch, 'save'), patch.object(watch, 'submit', side_effect=['1','2','3','4','5']) as submit:
            watch.transition(Path('/tmp/unused'), Path('/exports/job_5980/manifest.json'))
        calls = [c.kwargs for c in submit.call_args_list]
        self.assertEqual('visual_finetune_v1/freeze_v2.sbatch', calls[3]['script'])
        self.assertEqual(('1','3'), calls[3]['dependencies'])
        self.assertEqual('visual_finetune_v1/train_v2.sbatch', calls[4]['script'])
        self.assertEqual(('4',), calls[4]['dependencies'])

    def test_unready_cannot_submit_any_stage(self):
        with patch.object(watch, 'read', return_value=dict(gate=dict(quantitative_ready=False))), \
             patch.object(watch, 'submit') as submit:
            with self.assertRaises(AssertionError):
                watch.transition(Path('/tmp/unused'), Path('/exports/job_5980/manifest.json'))
        submit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
