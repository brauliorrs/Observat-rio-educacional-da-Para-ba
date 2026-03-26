import argparse
from pathlib import Path

import basedosdados as bd

from study_config import parse_municipios, resolve_municipios


def build_query(ano_ini: int, ano_fim: int, municipios: list[str]) -> str:
    clean_codes = [codigo.strip() for codigo in municipios if codigo.strip()]
    if not clean_codes:
        raise ValueError("Informe ao menos um codigo de municipio.")

    if len(clean_codes) == 1:
        municipio_filter = f"id_municipio_candidato = '{clean_codes[0]}'"
    else:
        values = ", ".join(f"'{codigo}'" for codigo in clean_codes)
        municipio_filter = f"id_municipio_candidato IN ({values})"

    return f"""
    SELECT
      ano,
      id_municipio_candidato,
      nome_curso,
      turno,
      COUNT(1) AS total_inscricoes
    FROM `basedosdados.br_mec_sisu.microdados`
    WHERE ano BETWEEN {ano_ini} AND {ano_fim}
      AND {municipio_filter}
    GROUP BY ano, id_municipio_candidato, nome_curso, turno
    ORDER BY ano, id_municipio_candidato, total_inscricoes DESC
    """


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--billing-project", required=True, help="Projeto de billing do BigQuery")
    parser.add_argument("--ano-ini", type=int, default=2017)
    parser.add_argument("--ano-fim", type=int, default=2022)
    parser.add_argument("--municipio", help="Codigo IBGE de um municipio")
    parser.add_argument("--municipios", help="Lista de codigos IBGE separada por virgula")
    parser.add_argument("--municipios-file", help="CSV de referencia com a coluna municipio_ibge")
    parser.add_argument("--out", default="data/raw/sisu_paraiba_ifpb_superiores_2017_2022_agg.csv")
    args = parser.parse_args()

    municipios = parse_municipios(args.municipios)
    if args.municipio:
        municipios.append(args.municipio)
    resolved, _ = resolve_municipios(municipios, args.municipios_file)

    query = build_query(args.ano_ini, args.ano_fim, resolved)

    print("Executando consulta no BigQuery via basedosdados...")
    df = bd.read_sql(query=query, billing_project_id=args.billing_project)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"Arquivo agregado salvo em: {out_path.resolve()}")
    print(f"Linhas retornadas: {len(df)}")
    print(f"Municipios no recorte: {len(set(resolved))}")


if __name__ == "__main__":
    main()
