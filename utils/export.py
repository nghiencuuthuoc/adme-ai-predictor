from __future__ import annotations

import io
from typing import Any

import pandas as pd


def flatten_predictions(predictions: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for category, values in predictions.items():
        if not isinstance(values, dict):
            continue
        for metric, value in values.items():
            rows.append(
                {
                    "category": category,
                    "metric": metric,
                    "value": value,
                }
            )
    return pd.DataFrame(rows)


def descriptors_frame(descriptors: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [{"descriptor": key, "value": value} for key, value in descriptors.items()]
    )


def export_csv_bytes(descriptors: dict[str, float], predictions: dict[str, Any]) -> bytes:
    output = io.StringIO()
    flatten_predictions(predictions).to_csv(output, index=False)
    output.write("\n")
    descriptors_frame(descriptors).to_csv(output, index=False)
    return output.getvalue().encode("utf-8")


def export_excel_bytes(smiles: str, descriptors: dict[str, float], predictions: dict[str, Any]) -> bytes:
    from openpyxl.styles import Font, PatternFill

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        summary = pd.DataFrame([{"smiles": smiles, "prediction_sections": len(predictions)}])
        summary.to_excel(writer, sheet_name="Summary", index=False)
        descriptors_frame(descriptors).to_excel(writer, sheet_name="Descriptors", index=False)
        flatten_predictions(predictions).to_excel(writer, sheet_name="Predictions", index=False)

        for sheet in writer.book.worksheets:
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            for column in sheet.columns:
                width = max(len(str(cell.value or "")) for cell in column) + 2
                sheet.column_dimensions[column[0].column_letter].width = min(width, 40)

    return output.getvalue()


def export_markdown(smiles: str, descriptors: dict[str, float], predictions: dict[str, Any], source: str) -> str:
    descriptor_table = descriptors_frame(descriptors).to_markdown(index=False)
    prediction_table = flatten_predictions(predictions).to_markdown(index=False)
    return (
        f"# ADME Prediction Report\n\n"
        f"- **SMILES**: `{smiles}`\n"
        f"- **Prediction source**: {source}\n\n"
        f"## Molecular Descriptors\n\n{descriptor_table}\n\n"
        f"## ADME Predictions\n\n{prediction_table}\n"
    )
