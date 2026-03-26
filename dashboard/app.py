import json
from pathlib import Path

import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
MANIFEST_PATH = PROCESSED_DIR / "study_manifest.json"


def load_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(
            "Manifesto de estudo nao encontrado. Rode primeiro `python ranking_paraiba.py --billing-project ...`."
        )
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def get_output_name(outputs: dict[str, str], prefix: str, exclude: str | None = None) -> str:
    for key, value in outputs.items():
        if key.startswith(prefix) and (exclude is None or exclude not in key):
            return value
    raise KeyError(f"Nao encontrei saida para {prefix}")


@st.cache_data
def load_data() -> tuple[dict, dict[str, pd.DataFrame]]:
    manifest = load_manifest()
    outputs = manifest["outputs"]
    data = {
        "cursos_total": pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "ranking_cursos_", "_por_")),
        "turnos_total": pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "ranking_turnos_", "_por_")),
        "cursos_ano": pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "ranking_cursos_por_ano_")),
        "municipios_total": pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "ranking_municipios_")),
        "cursos_municipio": pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "ranking_cursos_por_municipio_")),
    }
    if any(key.startswith("resumo_aderencia_oferta_ifpb_") for key in outputs):
        data["resumo_aderencia"] = pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "resumo_aderencia_oferta_ifpb_"))
        data["aderencia_oferta"] = pd.read_csv(PROCESSED_DIR / get_output_name(outputs, "aderencia_oferta_ifpb_"))
    return manifest, data


def format_int(value: int) -> str:
    return f"{int(value):,}".replace(",", ".")


def main() -> None:
    st.set_page_config(page_title="Observatorio Educacional da Paraiba", layout="wide")
    manifest, data = load_data()

    st.title("Observatorio Educacional da Paraiba")
    st.caption(
        f"Recorte atual: SiSU Paraiba IFPB. Fase 1 do projeto: cursos superiores via SiSU. Estudo ativo: {manifest['study_label']} ({manifest['ano_ini']}-{manifest['ano_fim']})."
    )

    total_inscricoes = int(data["cursos_total"]["total_inscricoes"].sum())
    col1, col2, col3 = st.columns(3)
    col1.metric("Inscricoes no recorte", format_int(total_inscricoes))
    col2.metric("Municipios no recorte", format_int(manifest["municipios_unicos"]))
    col3.metric("Fase", manifest["phase_label"])

    st.subheader("Municipios com maior volume")
    st.bar_chart(data["municipios_total"].head(15).set_index("municipio")["total_inscricoes"], height=380)

    st.subheader("Top cursos no periodo")
    st.bar_chart(data["cursos_total"].head(15).set_index("curso")["total_inscricoes"], height=420)

    st.subheader("Turnos no periodo")
    st.dataframe(data["turnos_total"], use_container_width=True, hide_index=True)

    if "resumo_aderencia" in data:
        st.subheader("Aderencia a oferta superior do IFPB")
        st.dataframe(data["resumo_aderencia"], use_container_width=True, hide_index=True)

    municipios = data["cursos_municipio"]["municipio"].dropna().sort_values().unique().tolist()
    selected = st.selectbox("Detalhar municipio", municipios, index=0 if municipios else None)
    if selected:
        filtered = data["cursos_municipio"][data["cursos_municipio"]["municipio"] == selected]
        st.subheader(f"Cursos mais recorrentes em {selected}")
        st.dataframe(filtered.head(20), use_container_width=True, hide_index=True)
        if "aderencia_oferta" in data:
            oferta_local = data["aderencia_oferta"][data["aderencia_oferta"]["municipio"] == selected]
            st.subheader(f"Aderencia a oferta do IFPB em {selected}")
            st.dataframe(oferta_local.head(20), use_container_width=True, hide_index=True)

    st.subheader("Serie anual agregada de cursos")
    st.dataframe(data["cursos_ano"].head(30), use_container_width=True, hide_index=True)

    st.subheader("Nota metodologica")
    st.markdown(
        """
        - Esta base usa o SiSU, portanto o foco inicial e o ensino superior.
        - Picui permanece dentro do recorte estadual.
        - A ampliacao para cursos tecnicos deve entrar em uma segunda fase com outra fonte de dados.
        """
    )


if __name__ == "__main__":
    main()
