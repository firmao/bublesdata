# Tabela `01_participants`

Uma linha por participante da coorte analítica do estudo OpenHeal TEA (n = 76). Reúne grupo, dados demográficos e o número de partidas válidas em cada dia.

Arquivos: `01_participants.xlsx` (aba `data`: os dados; aba `codebook`: uma linha por coluna, em inglês) e este `01_participants.md` (explicação em português; o codebook completo está na última seção). Gerados por `build.py` a partir das planilhas limpas do estudo.

## O estudo em uma linha

Crianças e adolescentes com TEA (GE) e controles pareados (GC) jogaram um jogo de rastreamento de mãos (estourar bolhas na tela). No dia 1 os dois grupos jogaram 3 partidas; no dia 2, só o GE jogou mais 3. Os dados de desempenho e de movimento de cada partida estão nas tabelas por partida (`03_matches`, `04_kinematics_match`, `05_kinematics_window`), ligadas a esta pelo `id_study`.

## Desenho e chaves

- **Unidade desta tabela:** o participante.
- **Chave:** `id_study`. É a mesma chave das tabelas por partida.
- **Grupos:** `group`. GE = TEA confirmado pela CARS-2 (n = 38); GC = controle sem TEA (n = 38), recrutado 1:1 pareado por sexo e idade. É o fator principal do estudo e a única classificação usada: não há subgrupos diagnósticos. Por construção, sexo e idade não diferem entre os grupos (7 F / 31 M em cada; 13,8 vs 13,5 anos).
- **Sessões:** `n_matches_day1` e `n_matches_day2` dizem quantas partidas válidas o participante tem em cada dia na `03_matches`. GC tem `n_matches_day2 = 0` sempre (desenho do estudo). No GE, 36 têm dia 2 e 2 não voltaram.

## Colunas

| Coluna | Valores | Significado |
|---|---|---|
| `id_study` | inteiro | Identificador do participante. Chave para as outras tabelas. |
| `group` | GE / GC | GE = transtorno do espectro autista (CARS-2); GC = controle. |
| `sex` | female / male | Sexo. 14 meninas, 62 meninos. |
| `age` | anos | Idade nas sessões de jogo. 5 a 24. |
| `n_matches_day1` | 2-3 | Quantas partidas válidas o participante tem no dia 1 (3, ou 2 se uma foi perdida por falha de captura). |
| `n_matches_day2` | 0-3 | Quantas partidas válidas tem no dia 2 (só GE; 0 = não tem dia 2). |

## Observações para a análise

- `group` e `sex` vêm como texto; `age` e os `n_matches_*` são inteiros.
- Para cruzar com desempenho e cinemática, juntar com `03_matches` ou `04_kinematics_match` por `id_study` (uma linha por partida). `group`, `sex` e `age` existem só aqui.
- Sexo e idade são variáveis de pareamento, não covariáveis candidatas; a distribuição por idade é larga (5 a 24 anos) e idêntica entre grupos.

## Codebook

Uma linha por coluna, na ordem da tabela (gerado por `build.py`; igual à aba `codebook` do `01_participants.xlsx`).

| column         | block        | unit / range   | description                                                                                                        | interpretation                                                                  | source                 |
|:---------------|:-------------|:---------------|:-------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------|:-----------------------|
| id_study       | id           | -              | Participant id in the study; key to the match tables                                                               |                                                                                 | data/participants.xlsx |
| group          | design       | GE / GC        | GE = autism spectrum disorder, confirmed by CARS-2; GC = control without ASD, recruited 1:1 matched by sex and age | main factor of the study                                                        | data/participants.xlsx |
| sex            | demographics | female / male  | Sex                                                                                                                |                                                                                 | data/participants.xlsx |
| age            | demographics | years          | Age at the game sessions                                                                                           |                                                                                 | data/participants.xlsx |
| n_matches_day1 | sessions     | 2-3            | Valid matches of the participant on day 1 (rows in 03_matches with day = 1)                                        | 3 for 74 participants, 2 for 2 (capture failure)                                | data/matches.xlsx      |
| n_matches_day2 | sessions     | 0-3            | Valid matches on day 2 (GE only; 0 = no day 2)                                                                     | GC: always 0 (study design). GE: 35 with 3, 1 with 2, 2 with 0 (did not return) | data/matches.xlsx      |

Notes

- One row per participant of the analytic cohort (n = 76: 38 GE, 38 GC). Key: id_study links to 03_matches, 04_kinematics_match and 05_kinematics_window.
- Groups are matched 1:1 by sex (7 female / 31 male in each) and age (GE 13.8 +- 4.0, GC 13.5 +- 3.7 years; range 5-24).
- ASD is the study's only classification (all GE participants assessed with the CARS-2); no diagnostic subgroups are used.
- Day 1 = OpenHeal game session of 3 matches, both groups. Day 2 = second session, GE only, about 3.5 months later. No questionnaires or functional tests are part of this dataset.
