import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pythonFiles import disease
from pythonFiles.disease import Disease, contagiousness_from_r0


class DiseaseContagiousnessTests(unittest.TestCase):
    def test_contagiousness_accepts_probability_bounds(self):
        self.assertEqual(Disease("None", "0", 0).contagiousness, 0)
        self.assertEqual(Disease("Certain", "1", 1).contagiousness, 1)

    def test_contagiousness_rejects_values_outside_probability_range(self):
        for value in (-0.01, 1.01, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Disease("Invalid", "0", value)

    def test_r0_is_converted_to_per_contact_probability(self):
        self.assertEqual(contagiousness_from_r0(2), 0.5)
        self.assertEqual(contagiousness_from_r0(1), 0)

    def test_r0_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            contagiousness_from_r0(0.9)

    def test_registration_saves_r0_and_derived_probability(self):
        original_diseases = disease.DISEASES.copy()
        original_order = list(disease.DISEASE_ORDER)
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with patch.object(disease, "DISEASES_DIR", Path(temp_dir)):
                    disease.register_custom_disease(
                        "Example", "01", r0_estimate=2
                    )
                    saved = json.loads(
                        (Path(temp_dir) / "example.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(saved["r0_estimate"], 2)
                    self.assertEqual(saved["contagiousness"], 0.5)
        finally:
            disease.DISEASES.clear()
            disease.DISEASES.update(original_diseases)
            disease.DISEASE_ORDER[:] = original_order


if __name__ == "__main__":
    unittest.main()
