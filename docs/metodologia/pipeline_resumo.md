# Pipeline estadual (resumo executivo)

## Objetivo

Reproduzir, de forma auditavel, a extracao e a organizacao de inscricoes no
SiSU para municipios da Paraiba com presenca do IFPB, preservando Picui como
parte do recorte.

## Fonte de dados

- Tabela: `basedosdados.br_mec_sisu.microdados`
- Acesso: BigQuery via biblioteca `basedosdados`
- Fase 1: ensino superior via SiSU
- Recorte territorial inicial: municipios listados em
  `data/reference/municipios_ifpb_pb.csv`

## Etapas

### 1. Extracao (`src/01_extract_sisu.py`)

- Executa a consulta SQL no BigQuery.
- Filtra os registros do periodo selecionado.
- Restringe o universo aos municipios definidos no estudo.
- Agrega os resultados por ano, municipio de residencia, curso e turno.

### 2. Rankings e tabelas (`src/02_aggregate_rankings.py`)

- Le o CSV agregado.
- Gera rankings estaduais agregados e desdobramentos por municipio.
- Quando houver arquivo de oferta superior do IFPB, gera tabelas de aderencia
  entre demanda observada e oferta local.
- Exporta CSVs e workbook consolidado.
- Escreve um manifesto com os caminhos e metadados do estudo ativo.

### 3. Figuras (`src/03_generate_figures.py`)

- Gera figuras de cursos, turnos e municipios.

### 4. Resumo de resultados (`src/04_export_report.py`)

- Consolida tabelas e figuras em um resumo em Markdown.

## Observacao

As contagens sao inscricoes no SiSU. Elas nao devem ser lidas automaticamente
como matricula, permanencia ou evasao.
