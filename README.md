# Observatorio Educacional da Paraiba

## SiSU Paraiba IFPB

Esta base nova amplia o estudo de Picui para um recorte estadual da Paraiba,
com foco inicial nos municipios que possuem unidades do IFPB. Como o SiSU
trata de ingresso no ensino superior, a fase 1 do projeto cobre cursos
superiores. A estrutura fica pronta para receber, em etapa posterior, bases
especificas de cursos tecnicos.

## Escopo inicial

- Territorio: municipios paraibanos com presenca do IFPB.
- Fase 1: ensino superior via SiSU.
- Unidade analitica: inscricoes agregadas por ano, municipio de residencia,
  curso e turno.
- Caso original preservado: Picui permanece dentro da nova base.

## Estrutura

```text
data/
  raw/
  processed/
  reference/
docs/
  metodologia/
  paper/
    figuras/
src/
dashboard/
ranking_paraiba.py
```

## Execucao rapida

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
python ranking_paraiba.py --billing-project SEU_PROJETO_GCP
streamlit run dashboard/app.py
```

## Estudos disponiveis

O comando padrao gera o estudo `paraiba_ifpb_superiores`, usando o cadastro em
`data/reference/municipios_ifpb_pb.csv`. Se quiser rodar um caso especifico,
voce pode informar manualmente os codigos de municipio.

Exemplos:

```bash
python ranking_paraiba.py --billing-project SEU_PROJETO_GCP
python ranking_paraiba.py --billing-project SEU_PROJETO_GCP --study-name picui --study-label "Picui (PB)" --municipio 2511400
python ranking_paraiba.py --billing-project SEU_PROJETO_GCP --municipios 2511400,2504009
```

## Oferta IFPB

O arquivo `data/reference/oferta_superior_ifpb_pb.csv` funciona como base de
comparacao entre a demanda observada no SiSU e a oferta superior local do IFPB.
Ele foi expandido com base no catalogo oficial de graduacao do Portal do
Estudante do IFPB. O arquivo complementar
`data/reference/status_oferta_superior_ifpb_pb.csv` registra onde houve ou nao
oferta superior presencial mapeada na consulta feita em 25 de marco de 2026.

## Observacao metodologica

As contagens representam inscricoes registradas no SiSU. Elas nao equivalem,
por si so, a matricula, permanencia, conclusao ou evasao.
