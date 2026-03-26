import argparse
import os
import subprocess
import sys
from pathlib import Path

from src.study_config import build_study_paths, parse_municipios, resolve_municipios


ROOT = Path(__file__).resolve().parent
PLACEHOLDERS = {"SEU_PROJETO_GCP", "MEU_PROJETO_GCP", "YOUR_GCP_PROJECT"}


def run_step(script: str, extra_args: list[str]) -> None:
    script_path = ROOT / "src" / script
    cmd = [sys.executable, str(script_path), *extra_args]
    subprocess.run(cmd, check=True, cwd=ROOT)


def resolve_billing_project(raw_value: str | None) -> str:
    candidates = [
        raw_value,
        os.getenv("BD_BILLING_PROJECT"),
        os.getenv("GOOGLE_CLOUD_PROJECT"),
        os.getenv("GCP_PROJECT"),
    ]
    for candidate in candidates:
        if candidate and candidate.strip() and candidate.strip() not in PLACEHOLDERS:
            return candidate.strip()

    raise ValueError(
        "Informe um projeto real de billing do BigQuery em --billing-project "
        "ou nas variaveis BD_BILLING_PROJECT / GOOGLE_CLOUD_PROJECT."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Executa o pipeline estadual do SiSU para a Paraiba."
    )
    parser.add_argument("--billing-project", help="Projeto de billing do BigQuery")
    parser.add_argument("--ano-ini", type=int, default=2017)
    parser.add_argument("--ano-fim", type=int, default=2025)
    parser.add_argument("--study-name", default="paraiba_ifpb_superiores")
    parser.add_argument("--study-label", default="Observatorio Educacional da Paraiba - municipios com IFPB")
    parser.add_argument("--municipio", help="Codigo IBGE de um municipio")
    parser.add_argument("--municipios", help="Lista de codigos IBGE separada por virgula")
    parser.add_argument(
        "--municipios-file",
        default="data/reference/municipios_ifpb_pb.csv",
        help="CSV de referencia com os municipios do estudo",
    )
    parser.add_argument("--metadata-file", help="CSV para rotular municipios no processamento")
    parser.add_argument(
        "--oferta-file",
        default="data/reference/oferta_superior_ifpb_pb.csv",
        help="CSV de oferta superior do IFPB para comparacao de aderencia",
    )
    args = parser.parse_args()

    billing_project = resolve_billing_project(args.billing_project)

    municipios = parse_municipios(args.municipios)
    if args.municipio:
        municipios.append(args.municipio)

    default_file = args.municipios_file if not municipios else None
    resolved_municipios, resolved_reference = resolve_municipios(municipios, default_file)

    metadata_file = args.metadata_file or default_file
    study_paths = build_study_paths(args.study_name, args.ano_ini, args.ano_fim, ROOT)

    run_step(
        "01_extract_sisu.py",
        [
            "--billing-project",
            billing_project,
            "--ano-ini",
            str(args.ano_ini),
            "--ano-fim",
            str(args.ano_fim),
            "--municipios",
            ",".join(resolved_municipios),
            "--out",
            str(study_paths["raw"]),
        ],
    )

    aggregate_args = [
        "--input",
        str(study_paths["raw"]),
        "--outdir",
        str(study_paths["processed_dir"]),
        "--workbook",
        study_paths["workbook"].name,
        "--study-name",
        args.study_name,
        "--study-label",
        args.study_label,
        "--ano-ini",
        str(args.ano_ini),
        "--ano-fim",
        str(args.ano_fim),
        "--manifest",
        str(study_paths["manifest"]),
    ]
    if metadata_file:
        aggregate_args.extend(["--metadata-file", metadata_file])
    if args.oferta_file:
        aggregate_args.extend(["--oferta-file", args.oferta_file])
    run_step("02_aggregate_rankings.py", aggregate_args)

    run_step("03_generate_figures.py", ["--manifest", str(study_paths["manifest"])])
    run_step(
        "04_export_report.py",
        [
            "--manifest",
            str(study_paths["manifest"]),
            "--out",
            str(study_paths["report"]),
        ],
    )

    print("Pipeline completo executado com sucesso.")
    print(f"Estudo ativo: {args.study_name} ({args.ano_ini}-{args.ano_fim})")
    print(f"Municipios no recorte: {len(set(resolved_municipios))}")
    if resolved_reference is not None:
        print(f"Unidades IFPB referenciadas: {len(resolved_reference)}")


if __name__ == "__main__":
    main()
