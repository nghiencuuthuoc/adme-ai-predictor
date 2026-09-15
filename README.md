# ADME-AI Predictor

Streamlit application for predicting and visualizing ADME/Tox properties from SMILES input, with export support for Excel, CSV, and Markdown.

## Features

- SMILES input with validation
- Molecular structure rendering with RDKit
- ADME/Tox and drug-likeness prediction workflow
- ADME-AI API integration via environment variables
- Descriptor-based fallback predictions when the API is unavailable
- Interactive Plotly charts:
  - ADME property distribution
  - Drug-likeness scoring
  - Bioavailability gauge
  - Radar profile
  - Descriptor comparison chart
- Export to:
  - `.xlsx`
  - `.csv`
  - `.md`
- Optional local prediction history

## Project Structure

```text
app.py
config.py
requirements.txt
utils/
  adme_predictor.py
  export.py
  molecule_utils.py
  visualization.py
```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Set environment variables in a local `.env` file if you have ADME-AI API access:

```env
ADME_API_URL=https://api.adme.ai/predict
ADME_API_KEY=your-token-if-required
ADME_API_TIMEOUT=20
ADME_HISTORY_PATH=.adme_history.json
```

If `ADME_API_URL` is not configured, is unavailable, or returns a non-standard payload, the app still produces descriptor-based fallback predictions and clearly labels the source in the UI.

## Run the App

```bash
streamlit run app.py
```

Use the default aspirin example:

```text
CC(=O)OC1=CC=CC=C1C(=O)O
```

## Notes

- Streamlit requirement is pinned to `>=1.59.2`
- Exported Excel files include formatted headers and separate sheets for summary, descriptors, and predictions
- Prediction history is stored locally and ignored by git
