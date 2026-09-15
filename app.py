from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from config import settings
from utils.adme_predictor import AdmePredictor
from utils.export import export_csv_bytes, export_excel_bytes, export_markdown, flatten_predictions
from utils.molecule_utils import molecule_to_base64_png, validate_smiles
from utils.visualization import (
    build_bioavailability_chart,
    build_comparison_chart,
    build_distribution_chart,
    build_drug_likeness_chart,
    build_radar_chart,
)


st.set_page_config(page_title=settings.app_name, page_icon="🧪", layout="wide")


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def save_history(path: Path, entry: dict) -> None:
    history = load_history(path)
    history.insert(0, entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history[: settings.max_history_items], indent=2), encoding="utf-8")


def render_molecule(smiles: str) -> None:
    image_data = molecule_to_base64_png(smiles)
    if image_data:
        st.image(f"data:image/png;base64,{image_data}", caption="Predicted molecule structure")


def render_prediction_tables(descriptors: dict[str, float], predictions: dict) -> None:
    st.subheader("Molecular descriptors")
    st.dataframe(pd.DataFrame([descriptors]).T.rename(columns={0: "value"}), use_container_width=True)

    st.subheader("ADME prediction details")
    for category, values in predictions.items():
        with st.expander(category.replace("_", " ").title(), expanded=(category == "absorption")):
            st.dataframe(pd.DataFrame([values]).T.rename(columns={0: "value"}), use_container_width=True)


def render_downloads(smiles: str, descriptors: dict[str, float], predictions: dict, source: str) -> None:
    st.subheader("Export results")
    csv_bytes = export_csv_bytes(descriptors, predictions)
    xlsx_bytes = export_excel_bytes(smiles, descriptors, predictions)
    markdown_text = export_markdown(smiles, descriptors, predictions, source)

    col1, col2, col3 = st.columns(3)
    col1.download_button("Download CSV", csv_bytes, file_name="adme_predictions.csv", mime="text/csv")
    col2.download_button(
        "Download Excel",
        xlsx_bytes,
        file_name="adme_predictions.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    col3.download_button("Download Markdown", markdown_text, file_name="adme_report.md", mime="text/markdown")


def main() -> None:
    st.title("🧪 ADME-AI Predictor")
    st.caption("Streamlit application for molecular ADME/Tox prediction, visualization, and export.")

    with st.sidebar:
        st.header("Input")
        smiles = st.text_input("SMILES notation", value="CC(=O)OC1=CC=CC=C1C(=O)O", help="Aspirin example provided.")
        run_prediction = st.button("Predict ADME profile", type="primary", use_container_width=True)
        st.divider()
        st.subheader("Prediction history")
        history = load_history(settings.history_path)
        if history:
            for item in history[:5]:
                st.caption(f"{item['smiles']} · {item['source']}")
        else:
            st.caption("No local prediction history yet.")

    is_valid, error_message = validate_smiles(smiles)
    if not is_valid:
        st.warning(error_message)
        return

    if not run_prediction:
        render_molecule(smiles)
        st.info("Provide a molecule and click **Predict ADME profile** to generate predictions.")
        return

    predictor = AdmePredictor()
    try:
        with st.spinner("Running ADME prediction and generating charts..."):
            result = predictor.predict(smiles)
    except Exception as exc:  # pragma: no cover - Streamlit UI flow
        st.error(f"Prediction failed: {exc}")
        return

    save_history(
        settings.history_path,
        {"smiles": result.smiles, "source": result.source, "drug_likeness": result.predictions.get("drug_likeness", {})},
    )

    for warning in result.warnings:
        st.warning(warning)

    summary_col, structure_col = st.columns([1.3, 1])
    with summary_col:
        st.subheader("Prediction summary")
        st.metric("Prediction source", result.source)
        st.metric(
            "Drug-likeness score",
            f"{float(result.predictions.get('drug_likeness', {}).get('overall_score', 0)):.2f}",
        )
        st.metric(
            "Bioavailability",
            f"{100 * float(result.predictions.get('absorption', {}).get('bioavailability_score', 0)):.1f}%",
        )
    with structure_col:
        render_molecule(smiles)

    render_prediction_tables(result.descriptors, result.predictions)
    render_downloads(result.smiles, result.descriptors, result.predictions, result.source)

    st.subheader("Visual analytics")
    chart1, chart2 = st.columns(2)
    distribution_chart = build_distribution_chart(result.predictions)
    if distribution_chart is not None:
        chart1.plotly_chart(distribution_chart, use_container_width=True)
    chart2.plotly_chart(build_drug_likeness_chart(result.predictions), use_container_width=True)

    chart3, chart4 = st.columns(2)
    chart3.plotly_chart(build_bioavailability_chart(result.predictions), use_container_width=True)
    chart4.plotly_chart(build_radar_chart(result.descriptors, result.predictions), use_container_width=True)

    st.plotly_chart(build_comparison_chart(result.descriptors), use_container_width=True)

    with st.expander("Flat prediction dataset"):
        st.dataframe(flatten_predictions(result.predictions), use_container_width=True)

    if result.raw_api_response:
        with st.expander("Raw API response"):
            st.json(result.raw_api_response)


if __name__ == "__main__":
    main()
