# Tabela `03_matches`

Uma linha por partida válida, n \= 333: identificação da partida e desempenho no jogo. Calculada a partir dos eventos bola a bola registrados pelo jogo.

Arquivos: `03_matches.xlsx` (aba `data`: os dados; aba `codebook`: uma linha por coluna, em inglês) e este `03_matches.md` (explicação em português; codebook completo na última seção).

## O jogo

Bolhas são lançadas na tela, uma a cada \~1 s, vindas de lados alternados, e o participante as estoura com as mãos, rastreadas por webcam. Cada partida dura cerca de 70 s e lança 66 bolhas (300 partidas) ou 78 (33). Cada sessão tem 3 partidas seguidas.

## Desenho e chaves

- **Unidade de análise:** a partida. Um participante tem 2 a 6 linhas (dia 1: 3, ou 2 por falha de captura; dia 2, só GE: 3, ou 2).  
- **Chaves:** `id_match` identifica a partida; `id_study` o participante (liga à `01_participants`); `day` (1-2) é a sessão e `moment` (1-3) a ordem da partida dentro da sessão. `id_study` \+ `day` \+ `moment` identifica a linha tanto quanto `id_match`.  
- **Mesmas partidas** da `04_kinematics_match` (mesmos `id_match`, mesma ordem).  
- **Sem faltantes.**  
- Linhas por grupo e dia: GC dia 1 \= 114; GE dia 1 \= 112, dia 2 \= 107\.

## Colunas

| Coluna | Unidade | Significado | Leitura |
| :---- | :---- | :---- | :---- |
| `id_match` | \- | Identificador da partida no banco do jogo | chave |
| `id_study` | \- | Identificador do participante | chave para `01_participants` |
| `day` | 1-2 | Sessão: 1 \= primeira (GE e GC); 2 \= segunda (só GE, \~3,5 meses depois) | fator "dia" (pré/pós no GE) |
| `match` | 1-3 | Ordem da partida dentro da sessão | fator "partida" (aprendizado ou fadiga dentro da sessão) |
| `n_balls` | contagem | Bolhas lançadas | 66 ou 78, conforme a configuração do jogo |
| `n_hits` | contagem | Bolhas estouradas | reproduz exatamente o % de acerto do jogo |
| `hit_rate` | 0-1 | `n_hits / n_balls` | **desfecho principal de desempenho**; maior \= melhor; independe de `n_balls` |
| `reaction_time_mean` | s | Média do intervalo lançamento → acerto, sobre os acertos válidos | menor \= mais rápido |
| `reaction_time_sd` | s | DP desse intervalo | menor \= mais consistente |
| `reaction_time_median` | s | Mediana desse intervalo | **desfecho principal de velocidade**; alternativa robusta à média |
| `reaction_time_q1`, `_q3` | s | Primeiro e terceiro quartis desse intervalo | com a mediana, mostram a assimetria dentro da partida |
| `reaction_time_iqr` | s | Intervalo interquartil, `q3 − q1` | alternativa robusta ao DP |
| `distance_mean` | 0-1 | Distância euclidiana lançamento → acerto, dividida pela diagonal da tela | 0 \= mesmo ponto, 1 \= cantos opostos; maior \= a bolha viajou mais antes de ser estourada |
| `distance_sd` | 0-1 | DP dessa distância |  |
| `distance_median` | 0-1 | Mediana dessa distância | alternativa robusta à média |
| `distance_q1`, `_q3` | 0-1 | Primeiro e terceiro quartis dessa distância |  |
| `distance_iqr` | 0-1 | Intervalo interquartil, `q3 − q1` | alternativa robusta ao DP |

Definições:

- **Acerto:** coordenada x do acerto diferente de 0, como registrado pelo jogo.  
- **Tempo de reação:** `HitTime` registrado pelo jogo. Dois acertos com `HitTime = 0` (em 22.374 bolhas) foram tratados como tempo inválido e excluídos só das estatísticas de tempo de reação.  
- **Distância:** normalizada pela diagonal da tela da partida (1920×1080 em 318 partidas; 1366×768 em 15 partidas do GC).  
- **Nível do jogo:** não está na tabela. Os registros de nível no banco estão incorretos e foram descartados; o único efeito do nível nos dados, o número de bolhas, está em `n_balls`.

## Observações para a análise

- `hit_rate` é uma proporção com teto: quartis 0,74 / 0,83 / 0,92, decil superior 0,97. Esperar assimetria à esquerda; considerar modelo binomial com `n_hits` e `n_balls`, ou transformação.  
- Medianas por grupo no dia 1: `hit_rate` GC 0,86-0,89 vs GE 0,79-0,82; `reaction_time_median` GC 1,16-1,37 s vs GE 1,65-1,75 s. No dia 2 o GE se aproxima do controle no tempo de reação (1,36-1,49 s).  
- `reaction_time_*` são calculados só sobre os acertos, então o número de observações por partida varia com `n_hits` (mínimo 26).  
- O dado bola a bola (22.374 linhas) existe e pode ser fornecido se for útil (modelo no nível da bola, com partida e participante como níveis).

## Codebook

Uma linha por coluna, na ordem da tabela (gerado por `build.py`; igual à aba `codebook` do `03_matches.xlsx`).

| column | description | unit / range | interpretation / notes |
| :---- | :---- | :---- | :---- |
| id\_match | Match identifier (game database) |  |  |
| id\_study | Participant identifier (= user\_id in the game database) |  |  |
| day | Session: 1 \= first assessment (GE and GC), 2 \= second assessment (GE only, after the intervention) | 1-2 |  |
| moment | Order of the match within the session | 1-3 |  |
| n\_balls | Balls launched in the match | count | 66 (300 matches) or 78 (33 matches), set by the game configuration; game levels are not carried (database records unreliable) |
| n\_hits | Balls hit (HitCoord\_x \!= 0\) | count | reproduces the game's hit\_percentage (2 matches differ by 1-2 points) |
| hit\_rate | n\_hits / n\_balls | 0-1 | higher \= better; independent of n\_balls |
| reaction\_time\_mean | Mean of HitTime (launch-to-hit interval) over valid hits | s | lower \= faster; hits with HitTime \= 0 excluded (2 balls in the dataset) |
| reaction\_time\_sd | SD of HitTime over valid hits | s | lower \= more consistent |
| reaction\_time\_median | Median of HitTime over valid hits | s | robust alternative to the mean |
| reaction\_time\_q1 | First quartile (25th percentile) of HitTime over valid hits | s |  |
| reaction\_time\_q3 | Third quartile (75th percentile) of HitTime over valid hits | s |  |
| reaction\_time\_iqr | Interquartile range, q3 \- q1, of HitTime over valid hits | s | robust alternative to the SD |
| distance\_mean | Mean launch-to-hit Euclidean distance over hits, divided by the screen diagonal of that match | 0-1 | 0 \= same point, 1 \= opposite corners |
| distance\_sd | SD of the normalised distance over hits | 0-1 |  |
| distance\_median | Median of the normalised distance over hits | 0-1 | robust alternative to the mean |
| distance\_q1 | First quartile (25th percentile) of the normalised distance over hits | 0-1 |  |
| distance\_q3 | Third quartile (75th percentile) of the normalised distance over hits | 0-1 |  |
| distance\_iqr | Interquartile range, q3 \- q1, of the normalised distance over hits | 0-1 | robust alternative to the SD |

Notes

- One row per match (n \= 333). Computed from data/balls.csv (one row per ball) and data/matches.xlsx; ball-level data in output/tables/balls\_normalized.csv. Reaction-time columns are NaN only if a match has no valid hit. Screen resolution is 1920x1080 (318 matches) or 1366x768 (15 matches, GC); coordinates are normalised by the match's own resolution.