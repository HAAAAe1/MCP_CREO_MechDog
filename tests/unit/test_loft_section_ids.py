"""BUG-028 public section references normalize before duplicate validation."""

import unittest

from schema import validate_operations


class LoftSectionIds(unittest.TestCase):
    def op(self, sections):
        return validate_operations([{"op": "loft", "label": "blend", "sections": sections}])[0]

    def test_integer_numeric_string_and_mixed_references(self):
        for supplied, expected in [
            ([40, 49], [40, 49]),
            (["40", "049"], [40, 49]),
            (["sk_a", "sk_b"], ["sk_a", "sk_b"]),
            (["40", "sk_b"], [40, "sk_b"]),
        ]:
            self.assertEqual(self.op(supplied)["sections"], expected)

    def test_normalized_duplicates_rejected(self):
        for supplied in ([40, "40"], ["040", "40"]):
            with self.assertRaisesRegex(ValueError, "distinct"):
                self.op(supplied)

    def test_labels_are_not_globally_converted(self):
        self.assertEqual(self.op(["sk_40", "sk_49"])["sections"], ["sk_40", "sk_49"])

    def test_invalid_native_id_rejected(self):
        for value in (-1, 2147483648, True):
            with self.assertRaises(ValueError):
                self.op([value, "sk_b"])
