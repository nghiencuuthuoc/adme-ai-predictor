from __future__ import annotations

import unittest
from unittest.mock import patch

import requests

from utils.adme_predictor import AdmePredictor, build_fallback_prediction, normalize_api_prediction
from utils.export import export_csv_bytes, export_markdown


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
        result = build_fallback_prediction(DESCRIPTORS)

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
        predictions = build_fallback_prediction(DESCRIPTORS)
        report = export_markdown("CCO", DESCRIPTORS, predictions, "Descriptor-based fallback")

        self.assertIn("# ADME Prediction Report", report)
        self.assertIn("- **Prediction source**: Descriptor-based fallback", report)
        self.assertIn("## Molecular Descriptors", report)
        self.assertIn("molecular_weight", report)
        self.assertIn("## ADME Predictions", report)
        self.assertIn("bioavailability_score", report)

    def test_export_markdown_escapes_user_controlled_fields(self) -> None:
        predictions = build_fallback_prediction(DESCRIPTORS)
        report = export_markdown("C*C", DESCRIPTORS, predictions, "API_[test]")

        self.assertIn("`C\\*C`", report)
        self.assertIn("API\\_\\[test\\]", report)

    def test_export_csv_uses_single_normalized_table(self) -> None:
        predictions = build_fallback_prediction(DESCRIPTORS)
        csv_text = export_csv_bytes("CCO", DESCRIPTORS, predictions).decode("utf-8")

        self.assertIn("smiles,record_type,category,metric,value", csv_text.splitlines()[0])
        self.assertIn("CCO,descriptor,molecular_descriptor,molecular_weight,180.159", csv_text)

    def test_predict_warns_on_request_failure(self) -> None:
        with (
            patch("utils.adme_predictor.validate_smiles", return_value=(True, "")),
            patch("utils.adme_predictor.calculate_descriptors", return_value=DESCRIPTORS),
            patch.object(AdmePredictor, "_call_api", side_effect=requests.RequestException("boom")),
        ):
            result = AdmePredictor(api_url="https://example.test").predict("CCO")

        self.assertEqual(result.source, "Descriptor-based fallback")
        self.assertTrue(result.warnings)
        self.assertIn("request failed", result.warnings[0].lower())

    def test_predict_warns_on_parse_failure(self) -> None:
        with (
            patch("utils.adme_predictor.validate_smiles", return_value=(True, "")),
            patch("utils.adme_predictor.calculate_descriptors", return_value=DESCRIPTORS),
            patch.object(AdmePredictor, "_call_api", side_effect=ValueError("bad payload")),
        ):
            result = AdmePredictor(api_url="https://example.test").predict("CCO")

        self.assertEqual(result.source, "Descriptor-based fallback")
        self.assertTrue(result.warnings)
        self.assertIn("could not parse", result.warnings[0].lower())

    def test_predict_keeps_extra_api_only_sections_at_the_end(self) -> None:
        with (
            patch("utils.adme_predictor.validate_smiles", return_value=(True, "")),
            patch("utils.adme_predictor.calculate_descriptors", return_value=DESCRIPTORS),
            patch.object(
                AdmePredictor,
                "_call_api",
                return_value={"absorption": {"bioavailability_score": 0.88}, "custom_section": {"score": 0.5}},
            ),
        ):
            result = AdmePredictor(api_url="https://example.test").predict("CCO")

        self.assertIn("custom_section", result.predictions)
        self.assertEqual(list(result.predictions)[-1], "custom_section")


if __name__ == "__main__":
    unittest.main()
