import argparse
import json
from pathlib import Path

import pandas as pd


def load_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")
    return pd.read_csv(path)


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Manifesto de estudo nao encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def format_table(df: pd.DataFrame, rows: int, column_map: dict[str, str]) -> str:
    display_df = df.head(rows).rename(columns=column_map).copy()
    for col in display_df.columns:
        if "Inscricoes" in col:
            display_df[col] = display_df[col].map(lambda x: f"{int(x):,}".replace(",", "."))
        if "pct" in col.lower():
            display_df[col] = display_df[col].map(lambda x: f"{float(x):.2f}")
    return display_df.to_markdown(index=False)


def get_output_name(outputs: dict[str, str], prefix: str, exclude: str | None = None) -> str:
    for key, value in outputs.items():
        if key.startswith(prefix) and (exclude is None or exclude not in key):
            return value
    raise KeyError(f"Nao encontrei saida para {prefix}")


def render_report(processed_dir: Path, figures_dir: Path, manifest: dict, top_n: int) -> str:
    outputs = manifest["outputs"]
    ranking_cursos = load_table(processed_dir / get_output_name(outputs, "ranking_cursos_", "_por_"))
    ranking_turnos = load_table(processed_dir / get_output_name(outputs, "ranking_turnos_", "_por_"))
    ranking_municipios = load_table(processed_dir / get_output_name(outputs, "ranking_municipios_"))
    cursos_por_ano = load_table(processed_dir / get_output_name(outputs, "ranking_cursos_por_ano_"))
    resumo_aderencia = None
    if any(key.startswith("resumo_aderencia_oferta_ifpb_") for key in outputs):
        resumo_aderencia = load_table(processed_dir / get_output_name(outputs, "resumo_aderencia_oferta_ifpb_"))

    total_inscricoes = int(ranking_cursos["total_inscricoes"].sum())
    period = f"{manifest['ano_ini']}-{manifest['ano_fim']}"
    study_slug = manifest["study_slug"]
    period_slug = f"{manifest['ano_ini']}_{manifest['ano_fim']}"

    figures = [
        figures_dir / f"fig1_top15_cursos_{study_slug}_{period_slug}.png",
        figures_dir / f"fig2_turnos_{study_slug}_{period_slug}.png",
        figures_dir / f"fig3_turnos_por_ano_{study_slug}_{period_slug}.png",
        figures_dir / f"fig4_municipios_{study_slug}_{period_slug}.png",
    ]

    lines = [
        "# Resumo de resultados",
        "",
        "## Escopo",
        f"- Estudo analisado: {manifest['study_label']}",
        f"- Fase atual: ensino superior via SiSU",
        f"- Periodo coberto: {period}",
        f"- Municipios no recorte: {manifest['municipios_unicos']}",
        f"- Total de inscricoes no periodo: {total_inscricoes}",
        "",
        "## Municipios com maior volume no periodo",
        format_table(
            ranking_municipios,
            min(top_n, len(ranking_municipios)),
            {"municipio": "Municipio", "id_municipio_candidato": "Codigo IBGE", "total_inscricoes": "Inscricoes"},
        ),
        "",
        "## Top cursos no periodo",
        format_table(ranking_cursos, top_n, {"curso": "Curso", "total_inscricoes": "Inscricoes"}),
        "",
        "## Distribuicao por turno",
        format_table(ranking_turnos, len(ranking_turnos), {"turno": "Turno", "total_inscricoes": "Inscricoes"}),
        "",
    ]

    if resumo_aderencia is not None:
        lines.extend(
            [
            "## Aderencia a oferta superior do IFPB",
            format_table(
                resumo_aderencia,
                min(top_n, len(resumo_aderencia)),
                {
                    "municipio": "Municipio",
                    "id_municipio_candidato": "Codigo IBGE",
                    "inscricoes_em_cursos_ofertados_ifpb": "Inscricoes em cursos ofertados",
                    "inscricoes_fora_da_oferta_ifpb": "Inscricoes fora da oferta",
                    "participacao_oferta_ifpb_pct": "Participacao oferta IFPB pct",
                },
            ),
            "",
            ]
        )

    lines.extend(
        [
            "## Serie anual de cursos",
            format_table(cursos_por_ano, top_n, {"ano": "Ano", "curso": "Curso", "total_inscricoes": "Inscricoes"}),
            "",
            "## Figuras disponiveis",
        ]
    )

    available_figures = [path for path in figures if path.exists()]
    if available_figures:
        lines.extend(f"- {path.as_posix()}" for path in available_figures)
    else:
        lines.append("- Nenhuma figura encontrada no diretorio informado.")

    lines.extend(
        [
            "",
            "## Nota metodologica",
            "- As contagens representam inscricoes registradas no SiSU, nao matriculas.",
            "- A fase 1 cobre cursos superiores, porque esta base usa o SiSU como fonte principal.",
            "- A ampliacao para cursos tecnicos deve entrar em uma etapa posterior com fonte especifica.",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", default="data/processed")
    parser.add_argument("--figdir", default="docs/paper/figuras")
    parser.add_argument("--out", default="docs/paper/resumo_resultados_paraiba_ifpb_superiores_2017_2025.md")
    parser.add_argument("--top-n", type=int, default=15)
    parser.add_argument("--manifest", default="data/processed/study_manifest.json")
    args = parser.parse_args()

    manifest = load_manifest(Path(args.manifest))
    report = render_report(Path(args.processed), Path(args.figdir), manifest, args.top_n)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    print("Resumo em Markdown gerado em:", out_path.resolve())


if __name__ == "__main__":
    main()
