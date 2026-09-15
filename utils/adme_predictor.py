from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import requests

from config import settings
from utils.molecule_utils import calculate_descriptors, validate_smiles

PREDICTION_SECTIONS = ("absorption", "distribution", "metabolism", "excretion", "toxicity", "drug_likeness")


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def build_fallback_prediction(descriptors: dict[str, float]) -> dict[str, Any]:
    mw = descriptors["molecular_weight"]
    logp = descriptors["logp"]
    tpsa = descriptors["tpsa"]
    hbd = descriptors["h_bond_donors"]
    hba = descriptors["h_bond_acceptors"]
    rotatable = descriptors["rotatable_bonds"]
    aromatic_rings = descriptors["aromatic_rings"]

    bioavailability = round(_clamp(0.95 - (max(logp - 3, 0) * 0.08) - (tpsa / 220) - (rotatable / 40)), 3)
    intestinal_absorption = round(_clamp(0.9 - (tpsa / 180) - (hbd * 0.04) + (0.08 if logp < 3 else 0)), 3)
    caco2 = round((-5.8 + (logp * 0.25) - (tpsa * 0.01)), 3)
    bbb = round(_clamp(0.75 + (logp * 0.06) - (tpsa / 160) - (hbd * 0.08)), 3)
    vdss = round(max(0.1, 0.8 + (logp * 0.35) + (aromatic_rings * 0.2)), 3)
    clearance = round(max(0.1, 1.8 - (mw / 350) - (logp * 0.12) + (rotatable * 0.03)), 3)
    half_life = round(max(0.5, 1.5 + (mw / 180) + (logp * 0.4)), 3)
    ames = round(_clamp(0.18 + (aromatic_rings * 0.07) + (0.08 if logp > 3.5 else 0)), 3)
    herg = round(_clamp(0.12 + (logp * 0.09) + (aromatic_rings * 0.05)), 3)

    lipinski_violations = int(
        (mw > 500)
        + (logp > 5)
        + (hbd > 5)
        + (hba > 10)
    )
    ghose_pass = 160 <= mw <= 480 and -0.4 <= logp <= 5.6 and 20 <= descriptors["heavy_atoms"] <= 70
    veber_pass = rotatable <= 10 and tpsa <= 140

    return {
        "absorption": {
            "human_intestinal_absorption": intestinal_absorption,
            "caco2_permeability_log_cm_s": caco2,
            "bioavailability_score": bioavailability,
            "p_gp_substrate_probability": round(_clamp(0.25 + (mw / 1000) + (logp * 0.05)), 3),
        },
        "distribution": {
            "bbb_penetration_probability": bbb,
            "vdss_log_l_kg": vdss,
            "fraction_unbound_probability": round(_clamp(0.7 - (logp * 0.08) + (tpsa / 300)), 3),
        },
        "metabolism": {
            "cyp3a4_substrate_probability": round(_clamp(0.35 + (logp * 0.07) + (aromatic_rings * 0.05)), 3),
            "cyp2d6_substrate_probability": round(_clamp(0.22 + (aromatic_rings * 0.05) + (mw / 1200)), 3),
            "metabolic_stability_probability": round(_clamp(0.8 - (logp * 0.05) - (aromatic_rings * 0.04)), 3),
        },
        "excretion": {
            "clearance_ml_min_kg": clearance,
            "half_life_hours": half_life,
            "renal_clearance_probability": round(_clamp(0.55 - (logp * 0.06) + (tpsa / 180)), 3),
        },
        "toxicity": {
            "ames_mutagenicity_probability": ames,
            "herg_inhibition_probability": herg,
            "drug_induced_liver_injury_probability": round(_clamp(0.2 + (logp * 0.06) + (mw / 1500)), 3),
        },
        "drug_likeness": {
            "lipinski_violations": lipinski_violations,
            "lipinski_pass": lipinski_violations == 0,
            "ghose_pass": ghose_pass,
            "veber_pass": veber_pass,
            "overall_score": round(
                (
                    int(lipinski_violations == 0)
                    + int(ghose_pass)
                    + int(veber_pass)
                    + bioavailability
                    + intestinal_absorption
                )
                / 5,
                3,
            ),
        },
    }


def normalize_api_prediction(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    normalized: dict[str, Any] = {}
    for section in PREDICTION_SECTIONS:
        section_data = payload.get(section, {})
        if isinstance(section_data, dict) and section_data:
            normalized[section] = section_data

    for section, section_data in payload.items():
        if section in normalized or section == "predictions":
            continue
        if isinstance(section_data, dict) and section_data:
            normalized[section] = section_data

    if normalized:
        return normalized

    predictions = payload.get("predictions")
    if isinstance(predictions, dict):
        return normalize_api_prediction(predictions)

    return {}


@dataclass
class PredictionResult:
    smiles: str
    descriptors: dict[str, float]
    predictions: dict[str, Any]
    source: str
    warnings: list[str]
    raw_api_response: dict[str, Any] | None = None


class AdmePredictor:
    def __init__(self, api_url: str | None = None, api_key: str | None = None, timeout: int | None = None):
        self.api_url = api_url or settings.adme_api_url
        self.api_key = api_key or settings.adme_api_key
        self.timeout = timeout or settings.request_timeout

    def predict(self, smiles: str) -> PredictionResult:
        is_valid, error_message = validate_smiles(smiles)
        if not is_valid:
            raise ValueError(error_message)

        descriptors = calculate_descriptors(smiles)
        warnings: list[str] = []
        raw_response = None
        api_predictions: dict[str, Any] = {}

        try:
            raw_response = self._call_api(smiles)
            api_predictions = normalize_api_prediction(raw_response or {})
            if not api_predictions:
                warnings.append("API response did not include normalized ADME sections; using descriptor-based fallback values.")
        except requests.RequestException as exc:
            warnings.append(f"ADME-AI API request failed: {exc}. Descriptor-based fallback predictions were generated instead.")
        except (ValueError, json.JSONDecodeError) as exc:
            warnings.append(f"Could not parse ADME-AI API response: {exc}. Descriptor-based fallback predictions were generated instead.")

        fallback_predictions = build_fallback_prediction(descriptors)
        ordered_sections = list(fallback_predictions) + [section for section in api_predictions if section not in fallback_predictions]
        predictions = {
            section: {
                **fallback_predictions.get(section, {}),
                **api_predictions.get(section, {}),
            }
            for section in ordered_sections
        }
        source = "ADME-AI API" if api_predictions else "Descriptor-based fallback"

        return PredictionResult(
            smiles=smiles,
            descriptors=descriptors,
            predictions=predictions,
            source=source,
            warnings=warnings,
            raw_api_response=raw_response,
        )

    def _call_api(self, smiles: str) -> dict[str, Any] | None:
        if not self.api_url:
            raise requests.RequestException("ADME_API_URL is not configured")

        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        response = requests.post(
            self.api_url,
            json={"smiles": smiles},
            headers=headers,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
