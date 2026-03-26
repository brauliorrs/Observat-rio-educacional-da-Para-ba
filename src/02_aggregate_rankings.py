import argparse
from pathlib import Path

import pandas as pd

from study_config import load_reference, normalize_course_name, slugify, write_manifest


REQUIRED_COLUMNS = {
    "ano",
    "id_municipio_candidato",
    "nome_curso",
    "turno",
    "total_inscricoes",
}


def load_aggregated_input(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS.difference(df.columns)
    if missing:
        cols = ", ".join(sorted(missing))
        raise ValueError(f"Arquivo de entrada sem colunas obrigatorias: {cols}")

    df = df.copy()
    df["ano"] = df["ano"].astype(int)
    df["id_municipio_candidato"] = df["id_municipio_candidato"].astype(str).str.strip()
    df["nome_curso"] = df["nome_curso"].fillna("NAO INFORMADO").astype(str).str.strip()
    df["turno"] = df["turno"].fillna("NAO INFORMADO").astype(str).str.strip()
    df["total_inscricoes"] = df["total_inscricoes"].fillna(0).astype(int)
    return df


def attach_reference(df: pd.DataFrame, reference_path: str | None) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    if not reference_path:
        enriched = df.copy()
        enriched["municipio"] = enriched["id_municipio_candidato"]
        return enriched, None

    reference = load_reference(reference_path)
    municipality_map = reference[["municipio_ibge", "municipio"]].drop_duplicates()
    enriched = df.merge(
        municipality_map,
        left_on="id_municipio_candidato",
        right_on="municipio_ibge",
        how="left",
    ).drop(columns=["municipio_ibge"])
    enriched["municipio"] = enriched["municipio"].fillna(enriched["id_municipio_candidato"])
    return enriched, reference


def load_oferta(path: str | None) -> pd.DataFrame | None:
    if not path:
        return None

    oferta_path = Path(path)
    if not oferta_path.exists():
        return None

    oferta = pd.read_csv(oferta_path, dtype={"municipio_ibge": str})
    required = {"municipio_ibge", "municipio", "unidade_ifpb", "curso_ofertado"}
    missing = required.difference(oferta.columns)
    if missing:
        cols = ", ".join(sorted(missing))
        raise ValueError(f"Oferta sem colunas obrigatorias: {cols}")

    oferta = oferta.copy()
    oferta["municipio_ibge"] = oferta["municipio_ibge"].astype(str).str.strip()
    oferta["municipio"] = oferta["municipio"].astype(str).str.strip()
    oferta["curso_ofertado"] = oferta["curso_ofertado"].map(normalize_course_name)
    return oferta


def build_oferta_outputs(df: pd.DataFrame, oferta: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
    if oferta is None or oferta.empty:
        return {}

    demanda = df.copy()
    demanda["curso_norm"] = demanda["nome_curso"].map(normalize_course_name)

    oferta_local = oferta.copy()
    if "tipo_curso" not in oferta_local.columns:
        oferta_local["tipo_curso"] = "superior"
    if "situacao_referencia" not in oferta_local.columns:
        oferta_local["situacao_referencia"] = "nao_informado"

    aderencia = (
        demanda.groupby(["id_municipio_candidato", "municipio", "curso_norm"], as_index=False)["total_inscricoes"]
        .sum()
        .merge(
            oferta_local[["municipio_ibge", "municipio", "unidade_ifpb", "curso_ofertado", "tipo_curso", "situacao_referencia"]],
            left_on=["id_municipio_candidato", "curso_norm"],
            right_on=["municipio_ibge", "curso_ofertado"],
            how="left",
        )
    )
    aderencia["curso_na_oferta_ifpb"] = aderencia["curso_ofertado"].notna()
    aderencia["unidade_ifpb"] = aderencia["unidade_ifpb"].fillna("NAO MAPEADO")
    aderencia["tipo_curso"] = aderencia["tipo_curso"].fillna("nao_informado")
    aderencia["situacao_referencia"] = aderencia["situacao_referencia"].fillna("sem_referencia")
    aderencia = aderencia.rename(columns={"curso_norm": "curso"})
    aderencia = aderencia[
        [
            "id_municipio_candidato",
            "municipio",
            "curso",
            "total_inscricoes",
            "curso_na_oferta_ifpb",
            "unidade_ifpb",
            "tipo_curso",
            "situacao_referencia",
        ]
    ].sort_values(["municipio", "curso_na_oferta_ifpb", "total_inscricoes", "curso"], ascending=[True, False, False, True])

    resumo = (
        aderencia.groupby(["id_municipio_candidato", "municipio", "curso_na_oferta_ifpb"], as_index=False)["total_inscricoes"]
        .sum()
        .pivot(index=["id_municipio_candidato", "municipio"], columns="curso_na_oferta_ifpb", values="total_inscricoes")
        .fillna(0)
        .reset_index()
    )
    if True not in resumo.columns:
        resumo[True] = 0
    if False not in resumo.columns:
        resumo[False] = 0
    resumo = resumo.rename(columns={True: "inscricoes_em_cursos_ofertados_ifpb", False: "inscricoes_fora_da_oferta_ifpb"})
    resumo["inscricoes_em_cursos_ofertados_ifpb"] = resumo["inscricoes_em_cursos_ofertados_ifpb"].astype(int)
    resumo["inscricoes_fora_da_oferta_ifpb"] = resumo["inscricoes_fora_da_oferta_ifpb"].astype(int)
    total = resumo["inscricoes_em_cursos_ofertados_ifpb"] + resumo["inscricoes_fora_da_oferta_ifpb"]
    resumo["participacao_oferta_ifpb_pct"] = ((resumo["inscricoes_em_cursos_ofertados_ifpb"] / total.where(total != 0, 1)) * 100).round(2)
    resumo = resumo.sort_values(["participacao_oferta_ifpb_pct", "municipio"], ascending=[False, True]).reset_index(drop=True)

    return {
        "aderencia_oferta_ifpb": aderencia,
        "resumo_aderencia_oferta_ifpb": resumo,
    }


def build_outputs(df: pd.DataFrame, study_slug: str, ano_ini: int, ano_fim: int, oferta: pd.DataFrame | None) -> dict[str, pd.DataFrame]:
    suffix = f"{study_slug}_{ano_ini}_{ano_fim}"

    ranking_cursos = (
        df.groupby("nome_curso", as_index=False)["total_inscricoes"]
        .sum()
        .rename(columns={"nome_curso": "curso"})
        .sort_values(["total_inscricoes", "curso"], ascending=[False, True])
        .reset_index(drop=True)
    )

    ranking_turnos = (
        df.groupby("turno", as_index=False)["total_inscricoes"]
        .sum()
        .sort_values(["total_inscricoes", "turno"], ascending=[False, True])
        .reset_index(drop=True)
    )

    ranking_cursos_por_ano = (
        df.groupby(["ano", "nome_curso"], as_index=False)["total_inscricoes"]
        .sum()
        .rename(columns={"nome_curso": "curso"})
        .sort_values(["ano", "total_inscricoes", "curso"], ascending=[True, False, True])
        .reset_index(drop=True)
    )

    ranking_turnos_por_ano = (
        df.groupby(["ano", "turno"], as_index=False)["total_inscricoes"]
        .sum()
        .sort_values(["ano", "total_inscricoes", "turno"], ascending=[True, False, True])
        .reset_index(drop=True)
    )

    ranking_municipios = (
        df.groupby(["id_municipio_candidato", "municipio"], as_index=False)["total_inscricoes"]
        .sum()
        .sort_values(["total_inscricoes", "municipio"], ascending=[False, True])
        .reset_index(drop=True)
    )

    ranking_cursos_por_municipio = (
        df.groupby(["id_municipio_candidato", "municipio", "nome_curso"], as_index=False)["total_inscricoes"]
        .sum()
        .rename(columns={"nome_curso": "curso"})
        .sort_values(["municipio", "total_inscricoes", "curso"], ascending=[True, False, True])
        .reset_index(drop=True)
    )

    ranking_turnos_por_municipio = (
        df.groupby(["id_municipio_candidato", "municipio", "turno"], as_index=False)["total_inscricoes"]
        .sum()
        .sort_values(["municipio", "total_inscricoes", "turno"], ascending=[True, False, True])
        .reset_index(drop=True)
    )

    outputs = {
        f"ranking_cursos_{suffix}": ranking_cursos,
        f"ranking_turnos_{suffix}": ranking_turnos,
        f"ranking_cursos_por_ano_{suffix}": ranking_cursos_por_ano,
        f"ranking_turnos_por_ano_{suffix}": ranking_turnos_por_ano,
        f"ranking_municipios_{suffix}": ranking_municipios,
        f"ranking_cursos_por_municipio_{suffix}": ranking_cursos_por_municipio,
        f"ranking_turnos_por_municipio_{suffix}": ranking_turnos_por_municipio,
    }

    oferta_outputs = build_oferta_outputs(df, oferta)
    for name, frame in oferta_outputs.items():
        outputs[f"{name}_{suffix}"] = frame

    return outputs


def save_outputs(outputs: dict[str, pd.DataFrame], outdir: Path, workbook_name: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    for base_name, frame in outputs.items():
        frame.to_csv(outdir / f"{base_name}.csv", index=False, encoding="utf-8-sig")

    ordered_keys = list(outputs.keys())
    with pd.ExcelWriter(outdir / workbook_name, engine="openpyxl") as writer:
        outputs[ordered_keys[0]].to_excel(writer, sheet_name="cursos_total", index=False)
        outputs[ordered_keys[1]].to_excel(writer, sheet_name="turnos_total", index=False)
        outputs[ordered_keys[2]].to_excel(writer, sheet_name="cursos_por_ano", index=False)
        outputs[ordered_keys[3]].to_excel(writer, sheet_name="turnos_por_ano", index=False)
        outputs[ordered_keys[4]].to_excel(writer, sheet_name="municipios_total", index=False)
        outputs[ordered_keys[5]].to_excel(writer, sheet_name="cursos_por_municipio", index=False)
        outputs[ordered_keys[6]].to_excel(writer, sheet_name="turnos_por_municipio", index=False)
        if len(ordered_keys) > 7:
            outputs[ordered_keys[7]].to_excel(writer, sheet_name="aderencia_oferta", index=False)
        if len(ordered_keys) > 8:
            outputs[ordered_keys[8]].to_excel(writer, sheet_name="resumo_aderencia", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/raw/sisu_paraiba_ifpb_superiores_2017_2025_agg.csv")
    parser.add_argument("--outdir", default="data/processed")
    parser.add_argument("--workbook", default="relatorio_paraiba_ifpb_superiores_2017_2025.xlsx")
    parser.add_argument("--study-name", default="paraiba_ifpb_superiores")
    parser.add_argument("--study-label", default="Observatorio Educacional da Paraiba - municipios com IFPB")
    parser.add_argument("--ano-ini", type=int, default=2017)
    parser.add_argument("--ano-fim", type=int, default=2025)
    parser.add_argument("--metadata-file", default="data/reference/municipios_ifpb_pb.csv")
    parser.add_argument("--oferta-file", default="data/reference/oferta_superior_ifpb_pb.csv")
    parser.add_argument("--manifest", default="data/processed/study_manifest.json")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Arquivo agregado nao encontrado: {input_path}")

    df = load_aggregated_input(input_path)
    enriched_df, reference = attach_reference(df, args.metadata_file)
    oferta = load_oferta(args.oferta_file)
    study_slug = slugify(args.study_name)
    outputs = build_outputs(enriched_df, study_slug, args.ano_ini, args.ano_fim, oferta)
    save_outputs(outputs, Path(args.outdir), args.workbook)

    manifest_payload = {
        "study_name": args.study_name,
        "study_slug": study_slug,
        "study_label": args.study_label,
        "phase_label": "superior",
        "ano_ini": args.ano_ini,
        "ano_fim": args.ano_fim,
        "raw_input": str(input_path.resolve()),
        "processed_dir": str(Path(args.outdir).resolve()),
        "workbook": str((Path(args.outdir) / args.workbook).resolve()),
        "metadata_file": str(Path(args.metadata_file).resolve()) if args.metadata_file else None,
        "oferta_file": str(Path(args.oferta_file).resolve()) if args.oferta_file and Path(args.oferta_file).exists() else None,
        "municipios_unicos": int(enriched_df["id_municipio_candidato"].nunique()),
        "outputs": {name: f"{name}.csv" for name in outputs},
        "reference_summary": None
        if reference is None
        else {
            "unidades_ifpb": int(len(reference)),
            "municipios_distintos": int(reference["municipio_ibge"].nunique()),
        },
        "oferta_summary": None
        if oferta is None
        else {
            "linhas_oferta": int(len(oferta)),
            "municipios_com_oferta": int(oferta["municipio_ibge"].nunique()),
        },
    }
    write_manifest(Path(args.manifest), manifest_payload)

    print("Rankings e tabelas gerados em:", Path(args.outdir).resolve())


if __name__ == "__main__":
    main()
