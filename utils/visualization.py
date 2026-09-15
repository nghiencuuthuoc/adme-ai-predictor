from __future__ import annotations

from typing import Any

import pandas as pd


def _plotly():
    import plotly.express as px
    import plotly.graph_objects as go

    return px, go


def build_prediction_frame(predictions: dict[str, Any]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for category, values in predictions.items():
        if not isinstance(values, dict):
            continue
        for metric, value in values.items():
            if isinstance(value, (int, float, bool)):
                records.append(
                    {
                        "category": category.replace("_", " ").title(),
                        "metric": metric.replace("_", " ").title(),
                        "value": float(value),
                    }
                )
    return pd.DataFrame(records)


def build_distribution_chart(predictions: dict[str, Any]):
    px, _ = _plotly()
    frame = build_prediction_frame(predictions)
    if frame.empty:
        return None
    return px.bar(frame, x="metric", y="value", color="category", title="ADME Property Distribution")


def build_radar_chart(descriptors: dict[str, float], predictions: dict[str, Any]):
    _, go = _plotly()
    molecular_weight = float(descriptors.get("molecular_weight", 0))
    likeness = predictions.get("drug_likeness", {})
    categories = [
        "Bioavailability",
        "Absorption",
        "BBB",
        "Safety",
        "Drug-likeness",
    ]
    values = [
        float(predictions.get("absorption", {}).get("bioavailability_score", 0)),
        float(predictions.get("absorption", {}).get("human_intestinal_absorption", 0)),
        float(predictions.get("distribution", {}).get("bbb_penetration_probability", 0)),
        1 - float(predictions.get("toxicity", {}).get("ames_mutagenicity_probability", 0)),
        float(likeness.get("overall_score", 0)),
    ]

    return go.Figure(
        data=[
            go.Scatterpolar(
                r=values + values[:1],
                theta=categories + categories[:1],
                fill="toself",
                name="Predicted Profile",
            )
        ],
        layout=go.Layout(
            title=f"ADME Radar Profile (MW {molecular_weight:.1f})",
            polar={"radialaxis": {"visible": True, "range": [0, 1]}},
        ),
    )


def build_drug_likeness_chart(predictions: dict[str, Any]):
    px, _ = _plotly()
    likeness = predictions.get("drug_likeness", {})
    frame = pd.DataFrame(
        [
            {"rule": "Lipinski", "pass_rate": 1.0 if likeness.get("lipinski_pass") else 0.0},
            {"rule": "Ghose", "pass_rate": 1.0 if likeness.get("ghose_pass") else 0.0},
            {"rule": "Veber", "pass_rate": 1.0 if likeness.get("veber_pass") else 0.0},
            {"rule": "Overall", "pass_rate": float(likeness.get("overall_score", 0))},
        ]
    )
    return px.bar(frame, x="rule", y="pass_rate", title="Drug-likeness Scoring", range_y=[0, 1])


def build_bioavailability_chart(predictions: dict[str, Any]):
    _, go = _plotly()
    score = float(predictions.get("absorption", {}).get("bioavailability_score", 0))
    return go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score * 100,
            title={"text": "Bioavailability Prediction (%)"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#2E86DE"}},
        )
    )


def build_comparison_chart(descriptors: dict[str, float]):
    px, _ = _plotly()
    frame = pd.DataFrame(
        [
            {"metric": "Molecular Weight", "observed": descriptors["molecular_weight"], "reference": 500},
            {"metric": "LogP", "observed": descriptors["logp"], "reference": 5},
            {"metric": "TPSA", "observed": descriptors["tpsa"], "reference": 140},
            {"metric": "Rotatable Bonds", "observed": descriptors["rotatable_bonds"], "reference": 10},
        ]
    )
    melted = frame.melt(id_vars="metric", var_name="series", value_name="value")
    return px.bar(melted, x="metric", y="value", color="series", barmode="group", title="Property Comparison")
