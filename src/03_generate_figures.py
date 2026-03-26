import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Manifesto de estudo nao encontrado: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def get_output_name(outputs: dict[str, str], prefix: str, exclude: str | None = None) -> str:
    for key, value in outputs.items():
        if key.startswith(prefix) and (exclude is None or exclude not in key):
            return value
    raise KeyError(f"Nao encontrei saida para {prefix}")


def save_barh(df: pd.DataFrame, ycol: str, xcol: str, title: str, outpath: Path, topn: int | None = None) -> None:
    plot_df = df.copy()
    if topn is not None:
        plot_df = plot_df.head(topn)
    plot_df = plot_df.sort_values(xcol, ascending=True)

    plt.figure(figsize=(10, 6))
    plt.barh(plot_df[ycol], plot_df[xcol], color="#1f4e5f")
    plt.title(title)
    plt.xlabel("Total de inscricoes")
    plt.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outpath, dpi=200)
    plt.close()


def save_turnos_por_ano(df_turnos_ano: pd.DataFrame, title: str, outpath: Path) -> None:
    pivot = (
        df_turnos_ano.pivot_table(index="ano", columns="turno", values="total_inscricoes", aggfunc="sum")
        .fillna(0)
        .sort_index()
    )

    plt.figure(figsize=(10, 6))
    for col in pivot.columns:
        plt.plot(pivot.index, pivot[col], marker="o", label=col)
    plt.title(title)
    plt.xlabel("Ano")
    plt.ylabel("Total de inscricoes")
    plt.legend()
    plt.tight_layout()
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(outpath, dpi=200)
    plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--processed", default="data/processed")
    parser.add_argument("--figdir", default="docs/paper/figuras")
    parser.add_argument("--manifest", default="data/processed/study_manifest.json")
    args = parser.parse_args()

    processed = Path(args.processed)
    figdir = Path(args.figdir)
    manifest = load_manifest(Path(args.manifest))
    outputs = manifest["outputs"]
    study_slug = manifest["study_slug"]
    period = f"{manifest['ano_ini']}_{manifest['ano_fim']}"
    study_label = manifest["study_label"]

    ranking_cursos = pd.read_csv(processed / get_output_name(outputs, "ranking_cursos_", "_por_"))
    ranking_turnos = pd.read_csv(processed / get_output_name(outputs, "ranking_turnos_", "_por_"))
    ranking_municipios = pd.read_csv(processed / get_output_name(outputs, "ranking_municipios_"))
    turnos_por_ano = pd.read_csv(processed / get_output_name(outputs, "ranking_turnos_por_ano_"))

    save_barh(
        ranking_cursos,
        ycol="curso",
        xcol="total_inscricoes",
        title=f"Top 15 cursos - {study_label}",
        outpath=figdir / f"fig1_top15_cursos_{study_slug}_{period}.png",
        topn=15,
    )
    save_barh(
        ranking_turnos,
        ycol="turno",
        xcol="total_inscricoes",
        title=f"Distribuicao por turno - {study_label}",
        outpath=figdir / f"fig2_turnos_{study_slug}_{period}.png",
    )
    save_turnos_por_ano(
        turnos_por_ano,
        title=f"Evolucao anual dos turnos - {study_label}",
        outpath=figdir / f"fig3_turnos_por_ano_{study_slug}_{period}.png",
    )
    save_barh(
        ranking_municipios,
        ycol="municipio",
        xcol="total_inscricoes",
        title=f"Top municipios do recorte - {study_label}",
        outpath=figdir / f"fig4_municipios_{study_slug}_{period}.png",
        topn=15,
    )

    print("Figuras geradas em:", figdir.resolve())


if __name__ == "__main__":
    main()
