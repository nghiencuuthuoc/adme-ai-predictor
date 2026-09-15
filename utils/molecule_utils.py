from __future__ import annotations

import base64
import io
from typing import Any


def _rdkit_modules() -> tuple[Any, Any, Any, Any]:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Draw, Lipinski

    return Chem, Crippen, Descriptors, Draw, Lipinski


def smiles_to_mol(smiles: str):
    Chem, _, _, _, _ = _rdkit_modules()
    return Chem.MolFromSmiles(smiles.strip())


def validate_smiles(smiles: str) -> tuple[bool, str]:
    if not smiles or not smiles.strip():
        return False, "Please provide a SMILES string."

    molecule = smiles_to_mol(smiles)
    if molecule is None:
        return False, "Invalid SMILES notation. Please check the input and try again."

    return True, ""


def molecule_to_base64_png(smiles: str, size: tuple[int, int] = (420, 300)) -> str | None:
    molecule = smiles_to_mol(smiles)
    if molecule is None:
        return None

    _, _, _, Draw, _ = _rdkit_modules()
    image = Draw.MolToImage(molecule, size=size)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def calculate_descriptors(smiles: str) -> dict[str, float]:
    molecule = smiles_to_mol(smiles)
    if molecule is None:
        raise ValueError("Cannot calculate descriptors for an invalid SMILES string.")

    _, Crippen, Descriptors, _, Lipinski = _rdkit_modules()
    return {
        "molecular_weight": round(Descriptors.MolWt(molecule), 3),
        "logp": round(Crippen.MolLogP(molecule), 3),
        "tpsa": round(Descriptors.TPSA(molecule), 3),
        "h_bond_donors": float(Lipinski.NumHDonors(molecule)),
        "h_bond_acceptors": float(Lipinski.NumHAcceptors(molecule)),
        "rotatable_bonds": float(Lipinski.NumRotatableBonds(molecule)),
        "aromatic_rings": float(Lipinski.NumAromaticRings(molecule)),
        "heavy_atoms": float(Lipinski.HeavyAtomCount(molecule)),
        "fraction_csp3": round(Lipinski.FractionCSP3(molecule), 3),
        "ring_count": float(Lipinski.RingCount(molecule)),
    }
