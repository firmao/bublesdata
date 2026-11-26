# Tabela `02_cohort`

Tabela 1 do manuscrito: descrição da coorte por grupo. Não é uma tabela de dados, é uma tabela pronta, para conferência. Os dados individuais estão na `01_participants`.

Arquivo: `02_cohort.xlsx`, duas abas.

## Aba `table1`

Idade, sexo e número de partidas válidas no dia 1, para todos e por grupo, com o teste de comparação entre GE e GC.

| Variável | Todos (n = 76) | GE, TEA (n = 38) | GC, controle (n = 38) | Teste | p | Tamanho de efeito |
|---|---|---|---|---|---|---|
| Idade (anos) | 13,6 (3,8); 13 [11, 15] | 13,8 (4,0); 13 [11, 15,8] | 13,5 (3,7); 13 [11, 15] | t de Welch | 0,745 | d = 0,07 |
| Sexo | fem. 14 (18%); masc. 62 (82%) | fem. 7 (18%); masc. 31 (82%) | fem. 7 (18%); masc. 31 (82%) | qui-quadrado | 1,000 | |
| Partidas válidas, dia 1 | 2: 2 (3%); 3: 74 (97%) | 2: 2 (5%); 3: 36 (95%) | 3: 38 (100%) | Fisher exato | 0,493 | |

Contínuas: média (DP); mediana [Q1, Q3]. Categóricas: n (%). Dia 2 (só GE): 36 dos 38 participantes; 35 com 3 partidas, 1 com 2.

Regra usada: Shapiro-Wilk nos dois grupos; se ambos p > 0,05, t de Welch e d de Cohen; senão Mann-Whitney U e r = z / √n. Categóricas: qui-quadrado, ou Fisher exato em tabelas 2×2 com alguma célula < 5. Alfa 0,05, sem correção de multiplicidade (tabela descritiva).

Sexo e idade são iguais entre grupos por construção (pareamento 1:1), não um achado.

## Aba `abnt_sex_group`

A mesma tabela sexo × grupo no formato ABNT (título numerado acima, fonte e p abaixo), em português, para o manuscrito.

## Relação com as outras tabelas

Tudo aqui pode ser recalculado a partir de `01_participants` (`age`, `sex`, `group`, `n_matches_day1`, `n_matches_day2`).
