# Dicionario de variaveis

Fonte principal: `basedosdados.br_mec_sisu.microdados`

## Variaveis originais utilizadas

- `ano`: ano de referencia do SiSU.
- `id_municipio_candidato`: codigo IBGE do municipio de residencia do candidato.
- `nome_curso`: nome do curso escolhido na inscricao.
- `turno`: turno associado ao curso escolhido.

## Variavel derivada

- `total_inscricoes`: contagem agregada de inscricoes para cada combinacao de
  ano, municipio de residencia, curso e turno.

## Observacoes analiticas

- A unidade analitica do pipeline e a inscricao agregada.
- O uso de `COUNT(1)` contabiliza registros da base filtrada, nao pessoas unicas.
- Como a fonte e o SiSU, a fase atual da base cobre ensino superior.
