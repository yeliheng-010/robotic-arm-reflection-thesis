import unittest
from sv_requests_v2 import decorate


class LabelTests(unittest.TestCase):
    def test_display_instruction_follows_random_colour_not_body_id(self):
        case = dict(item=dict(source='RedBlock', destination='BlueBin'),
            config=dict(appearance={'BlueBin':dict(color='红色', rgba=[.9,.1,.1,1.])}))
        bundle = dict(request=dict(task=dict(source='RedBlock', destination='BlueBin'), execution_semantics={}))
        result = decorate(bundle, case)
        self.assertEqual('红色箱子', result['request']['task_description']['destination'])
        self.assertEqual('BlueBin', result['request']['task']['destination'])
        self.assertEqual(result['direct_messages'][1], result['diagnostic_messages'][1])
        self.assertNotIn('appearance', result['request'])

    def test_original_configuration_labels(self):
        case = dict(item=dict(source='PurpleCapsule', destination='RedBin'), config=dict(appearance={}))
        bundle = dict(request=dict(execution_semantics={}))
        self.assertEqual('将紫色胶囊放入红色箱子', decorate(bundle, case)['request']['task_description']['instruction'])
