from __future__ import annotations

import unittest

from utils.adme_predictor import build_fallback_prediction, normalize_api_prediction
from utils.export import export_markdown


DESCRIPTORS = {
    "molecular_weight": 180.159,
    "logp": 1.2,
    "tpsa": 63.6,
    "h_bond_donors": 1.0,
    "h_bond_acceptors": 3.0,
    "rotatable_bonds": 3.0,
    "aromatic_rings": 1.0,
    "heavy_atoms": 13.0,
    "fraction_csp3": 0.11,
    "ring_count": 1.0,
}


class AdmeUtilityTests(unittest.TestCase):
    def test_build_fallback_prediction_has_required_sections(self) -> None:
        result = build_fallback_prediction("CCO", DESCRIPTORS)

        self.assertIn("absorption", result)
        self.assertIn("distribution", result)
        self.assertIn("metabolism", result)
        self.assertIn("excretion", result)
        self.assertIn("toxicity", result)
        self.assertIn("drug_likeness", result)
        self.assertGreaterEqual(result["drug_likeness"]["overall_score"], 0)
        self.assertLessEqual(result["drug_likeness"]["overall_score"], 1)

    def test_normalize_api_prediction_supports_nested_payloads(self) -> None:
        payload = {"predictions": {"absorption": {"bioavailability_score": 0.88}}}
        result = normalize_api_prediction(payload)

        self.assertEqual(result["absorption"]["bioavailability_score"], 0.88)

    def test_export_markdown_contains_sections(self) -> None:
        predictions = build_fallback_prediction("CCO", DESCRIPTORS)
        report = export_markdown("CCO", DESCRIPTORS, predictions, "Descriptor-based fallback")

        self.assertIn("# ADME Prediction Report", report)
        self.assertIn("## Molecular Descriptors", report)
        self.assertIn("## ADME Predictions", report)


if __name__ == "__main__":
    unittest.main()
