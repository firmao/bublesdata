# Tabelas para a análise estatística: estudo OpenHeal TEA (APAE)

Crianças e adolescentes com transtorno do espectro autista confirmado pela CARS-2 (GE, n \= 38\) e um grupo controle sem TEA pareado 1:1 por sexo e idade (GC, n \= 38\) jogaram um jogo de rastreamento de mãos por webcam (estourar bolhas na tela). **Dia 1**: uma sessão de 3 partidas, nos dois grupos. **Dia 2**: segunda sessão de 3 partidas, só no GE, cerca de 3,5 meses depois (36 dos 38 voltaram). Ao fim da última sessão de cada participante, a criança respondeu o System Usability Scale (SUS), com ajuda do pesquisador e do profissional da APAE. Não há outros questionários nem testes funcionais neste conjunto de dados.

Cada tabela tem um `.xlsx` (aba `data` com os dados, aba `codebook` com uma linha por coluna) e um `.md` que explica a tabela e repete o codebook no fim.

| Tabela | Uma linha por | Linhas | Conteúdo |
| :---- | :---- | :---- | :---- |
| `01_participants` | participante | 76 | grupo, sexo, idade, nº de partidas válidas no dia 1 e no dia 2 |
| `02_cohort` | (descritiva) | \- | Tabela 1 do manuscrito: idade, sexo e partidas por grupo, já com testes |
| `03_matches` | partida | 333 | identificação da partida e desempenho no jogo: acertos, tempo de reação, distância |
| `04_kinematics_match` | partida | 333 | cinemática das mãos na partida inteira: velocidade, trajeto, suavidade (SPARC, LDLJ), acoplamento entre mãos |
| `05_kinematics_window` | partida × janela | 1998 | as mesmas métricas de cinemática em 6 janelas de \~12 s dentro de cada partida |
| `06_analysis_plan.md` | \- | \- | plano de análise: perguntas, desfechos, modelos, sensibilidade, decisões em aberto |
| `07_consort.md` \+ `07_consort_flow.png/.svg` | \- | \- | fluxo da amostra (Figura 1\) e o texto *Participants* do Methods |
| `08_outcomes_by_group.png` | \- | \- | os três desfechos primários por grupo × dia × partida (descritivo) |
| `09_sus` | participante | 76 | usabilidade (SUS): 10 itens, escore 0-100 e a sessão em que foi respondido |

## Chaves e junções

- `id_study`: o participante. Está em todas as tabelas de dados. Na `09_sus` há uma linha por participante, como na 01\.  
- `id_match`: a partida. Está nas tabelas 03, 04 e 05\.  
- `day` (1-2) e `moment` (1-3): a sessão e a ordem da partida dentro dela. `id_study` \+ `day` \+ `moment` identifica a partida tanto quanto `id_match`.  
- `window` (1-6): a janela dentro da partida, só na 05\.

```
01_participants (id_study)
   ├── 09_sus (id_study)                                    1 participante : 1 linha
   └── 03_matches (id_match, id_study, day, moment)        1 participante : 2-6 partidas
         ├── 04_kinematics_match (id_match)                 1 partida : 1 linha
         └── 05_kinematics_window (id_match, window)        1 partida : 6 janelas
```

`03_matches` e `04_kinematics_match` têm as mesmas 333 partidas, na mesma ordem; juntam-se por `id_match`. `group`, `sex` e `age` estão só na `01_participants`: para usá-los por partida, juntar por `id_study`.

## Análise

O desenho completo está em `06_analysis_plan.md`. Em resumo: três desfechos primários por partida (`hit_rate`, `reaction_time_median`, `sparc_bilateral`) em duas análises, (A) GE vs GC no dia 1 e (B) GE dia 1 vs dia 2, ambas com modelos mistos com participante como efeito aleatório; janelas de 12 s como sensibilidade; curso temporal dentro da partida como exploratório. O SUS (09) é descritivo por grupo, com uma comparação GE vs GC.

&nbsp;