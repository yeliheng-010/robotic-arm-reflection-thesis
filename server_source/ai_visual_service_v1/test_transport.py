import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from copy import deepcopy
from prompts import messages
from f_common import sha
from vs_transport import validate, execute


class FakeGenerator:
    def prepare_images(self, prompts, paths):
        return None, dict(image_grid_thw=[[1, 2, 2], [1, 2, 2]])

    def generate(self, values):
        return dict(text='test_only')


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        (root/'manifest.json').write_text('{}')
        image = root/'frame.png'
        image.write_bytes(b'test_only_not_model_input')
        self.server = SimpleNamespace(root=root, calls=0, max_calls=2, max_decisions=4,
            conditions={'case'}, image_roots=[root], generator=FakeGenerator())
        self.body = dict(condition='case', mode='direct', ordinal=1, request={}, messages=messages({}, mode='direct'),
            visual=dict(paths=[str(image)]*2, sha256=[sha(image)]*2, order=['before', 'latest_after']))

    def test_duplicate_does_not_generate_again(self):
        execute(self.server, self.body)
        with self.assertRaises(FileExistsError):
            execute(self.server, self.body)
        self.assertEqual(1, self.server.calls)

    def test_tamper_and_prompt_mismatch(self):
        body = deepcopy(self.body)
        body['visual']['sha256'][0] = 'bad'
        with self.assertRaises(AssertionError):
            validate(body, self.server)
        body = deepcopy(self.body)
        body['messages'][1]['content'] = 'future_secret'
        with self.assertRaises(AssertionError):
            validate(body, self.server)

    def test_roots_and_budget(self):
        self.server.image_roots = [self.server.root/'other']
        with self.assertRaises(AssertionError):
            validate(self.body, self.server)
        self.server.image_roots = [self.server.root]
        self.server.calls = self.server.max_calls
        with self.assertRaises(AssertionError):
            execute(self.server, self.body)
