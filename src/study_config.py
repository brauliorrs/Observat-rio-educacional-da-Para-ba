import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "data" / "reference" / "municipios_ifpb_pb.csv"
DEFAULT_MANIFEST = ROOT / "data" / "processed" / "study_manifest.json"


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return normalized.strip("_") or "estudo"


def parse_municipios(raw_value: str | None) -> list[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def load_reference(path: str | Path | None) -> pd.DataFrame:
    reference_path = Path(path) if path else DEFAULT_REFERENCE
    if not reference_path.exists():
        raise FileNotFoundError(f"Arquivo de referencia nao encontrado: {reference_path}")

    df = pd.read_csv(reference_path, dtype={"municipio_ibge": str})
    required = {"municipio_ibge", "municipio", "unidade_ifpb", "tipo_unidade"}
    missing = required.difference(df.columns)
    if missing:
        cols = ", ".join(sorted(missing))
        raise ValueError(f"Referencia sem colunas obrigatorias: {cols}")

    df = df.copy()
    df["municipio_ibge"] = df["municipio_ibge"].astype(str).str.strip()
    df["municipio"] = df["municipio"].astype(str).str.strip()
    return df


def resolve_municipios(
    municipios: list[str] | None,
    municipios_file: str | Path | None,
) -> tuple[list[str], pd.DataFrame | None]:
    manual = [item.strip() for item in (municipios or []) if item.strip()]
    if manual and municipios_file:
        raise ValueError("Use municipios ou municipios-file, nao ambos ao mesmo tempo.")

    if municipios_file:
        reference = load_reference(municipios_file)
        resolved = reference["municipio_ibge"].drop_duplicates().tolist()
        return resolved, reference

    if manual:
        return manual, None

    return ["2511400"], None


def build_study_paths(
    study_name: str,
    ano_ini: int,
    ano_fim: int,
    root: Path | None = None,
) -> dict[str, Path]:
    base_root = root or ROOT
    study_slug = slugify(study_name)
    period = f"{ano_ini}_{ano_fim}"
    return {
        "raw": base_root / "data" / "raw" / f"sisu_{study_slug}_{period}_agg.csv",
        "processed_dir": base_root / "data" / "processed",
        "workbook": base_root / "data" / "processed" / f"relatorio_{study_slug}_{period}.xlsx",
        "figures_dir": base_root / "docs" / "paper" / "figuras",
        "report": base_root / "docs" / "paper" / f"resumo_resultados_{study_slug}_{period}.md",
        "manifest": DEFAULT_MANIFEST,
    }


def write_manifest(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_course_name(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value).strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.upper()
    text = re.sub(r"\(ABI\)", "", text)
    text = re.sub(r"\s+", " ", text)

    prefixes = [
        "BACHARELADO EM ",
        "LICENCIATURA EM ",
        "TECNOLOGIA EM ",
        "CURSO SUPERIOR DE TECNOLOGIA EM ",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            text = text[len(prefix):]

    return text.strip(" -")
