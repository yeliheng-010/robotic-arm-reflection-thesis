"""审计门禁的字段遗漏、额外变化及未预期签名必须拒绝。"""
import unittest
from qualified_scene_static_audit_v2.gate import (
    serialized_identity, FIELD_COUNT, COMPILED_SIGNATURE)


class IdentityGateTest(unittest.TestCase):
    def setUp(self):
        self.saved = {str(i): str(i) for i in range(FIELD_COUNT-1)}
        self.saved['signature'] = COMPILED_SIGNATURE
        self.loaded = dict(self.saved, signature='0')

    def test_expected_signature_only(self):
        self.assertEqual(FIELD_COUNT-1, serialized_identity(self.saved, self.loaded)['serialized_fields_matched'])

    def test_parameter_change_rejected(self):
        self.loaded['0'] = 'changed'
        with self.assertRaises(ValueError):
            serialized_identity(self.saved, self.loaded)

    def test_missing_field_rejected(self):
        self.loaded.pop('0')
        with self.assertRaises(ValueError):
            serialized_identity(self.saved, self.loaded)

    def test_extra_field_rejected(self):
        self.loaded['extra'] = '0'
        with self.assertRaises(ValueError):
            serialized_identity(self.saved, self.loaded)

    def test_unexpected_signature_rejected(self):
        self.loaded['signature'] = COMPILED_SIGNATURE
        with self.assertRaises(ValueError):
            serialized_identity(self.saved, self.loaded)

    def test_original_signature_change_rejected(self):
        self.saved['signature'] = '1'
        with self.assertRaises(ValueError):
            serialized_identity(self.saved, self.loaded)

    def test_field_rename_rejected(self):
        self.loaded['renamed'] = self.loaded.pop('0')
        with self.assertRaises(ValueError):
            serialized_identity(self.saved, self.loaded)
