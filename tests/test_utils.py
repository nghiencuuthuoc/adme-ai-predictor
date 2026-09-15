from __future__ import annotations

import unittest
from unittest.mock import patch

from utils.adme_predictor import AdmePredictor, build_fallback_prediction, normalize_api_prediction
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

    def test_predict_merges_partial_api_response_without_losing_fallback_values(self) -> None:
        with (
            patch("utils.adme_predictor.validate_smiles", return_value=(True, "")),
            patch("utils.adme_predictor.calculate_descriptors", return_value=DESCRIPTORS),
            patch.object(AdmePredictor, "_call_api", return_value={"absorption": {"bioavailability_score": 0.88}}),
        ):
            result = AdmePredictor(api_url="https://example.test").predict("CCO")

        self.assertEqual(result.predictions["absorption"]["bioavailability_score"], 0.88)
        self.assertIn("human_intestinal_absorption", result.predictions["absorption"])
        self.assertIn("distribution", result.predictions)
        self.assertEqual(list(result.predictions)[0], "absorption")

    def test_export_markdown_contains_sections(self) -> None:
        predictions = build_fallback_prediction("CCO", DESCRIPTORS)
        report = export_markdown("CCO", DESCRIPTORS, predictions, "Descriptor-based fallback")

        self.assertIn("# ADME Prediction Report", report)
        self.assertIn("## Molecular Descriptors", report)
        self.assertIn("## ADME Predictions", report)


if __name__ == "__main__":
    unittest.main()
