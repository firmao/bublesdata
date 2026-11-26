# Tabela `05_kinematics_window`

Uma linha por partida × janela, n = 1998 (333 partidas × 6 janelas): as mesmas métricas de cinemática da `04_kinematics_match`, calculadas em 6 blocos contíguos e iguais de cada partida (~12 s cada). Mesma fonte, mesmas funções, mesmo corte de 3,0 Hz.

Arquivos: `05_kinematics_window.xlsx` (aba `data`: os dados; aba `codebook`: uma linha por coluna, em inglês) e este `05_kinematics_window.md` (explicação em português; codebook completo na última seção).

Leia primeiro `04_kinematics_match.md`: a obtenção dos dados, a normalização e o significado de cada métrica são os mesmos e não se repetem aqui.

## Por que janelas

A partida inteira é a unidade primária, mas nenhum estudo publicado calcula o SPARC sobre uma sessão de mais de um minuto; a literatura segmenta em movimentos ponto a ponto, e a segmentação muda o valor. Segmentar por bolha não é limpo aqui: as bolhas são lançadas a cada ~1 s e a maioria dos alcances ainda está em curso quando a próxima é lançada. O compromisso são janelas de tempo fixas.

## Desenho e chaves

- **Unidade:** a janela dentro da partida. Chave: `id_match` + `window`. `id_study`, `day` e `moment` estão repetidos para facilitar.
- **Aninhamento:** janela ⊂ partida ⊂ sessão ⊂ participante (6 × 2-3 × 1-2 × 76).
- **Sem faltantes.**

## Colunas próprias desta tabela

| Coluna | Valores | Significado |
|---|---|---|
| `window` | 1-6 | Índice da janela: os frames da partida divididos em 6 blocos contíguos de tamanho igual, todos os frames usados |
| `phase` | early / middle / late | Terço da partida: early = janelas 1-2, middle = 3-4, late = 5-6 |
| `t_start`, `t_end` | s | Início e fim da janela, contados do início da partida (~12 s de duração) |
| `n_frames` | 72-116 | Frames na janela |
| `dt` | s | Passo de tempo da partida, igual em todas as suas janelas |

As demais colunas (`speed_mean_*`, `speed_sd_*`, `path_length_*`, `sparc_*`, `ldlj_*`, com sufixos `_left`, `_right`, `_bilateral`) têm o mesmo nome e a mesma leitura da `04_kinematics_match`, agora dentro da janela. `traj_corr_*` e `mirror_score` não são calculados por janela.

## Usos previstos

1. **Sensibilidade do resultado da partida inteira:** média das 6 janelas por partida, entrando no mesmo modelo misto que `sparc_bilateral` da `04_kinematics_match`.
2. **Evolução dentro da partida (exploratório):** modelo misto com janela aninhada em partida aninhada em participante, interação grupo × `phase` (aquecimento ou fadiga, e se difere por grupo).

## Observações para a análise

- O SPARC da janela (~ −4,7) não é comparável ao da partida inteira (~ −9,3): o espectro do perfil inteiro não é a média dos espectros das janelas. A correlação entre o valor da partida inteira e a média das janelas é r = 0,66.
- As janelas 1 e 6 são mais suaves (−4,5 vs ~ −4,75) e mais lentas (velocidade 0,62 e 0,66 vs ~0,73): o início e o fim da partida incluem segundos antes de as mãos entrarem em ação e depois da última bolha. Considerar isso ao interpretar `phase`.
- `ldlj_*` continua só descritivo, pelo mesmo motivo da `04_kinematics_match`.

## Codebook

Uma linha por coluna, na ordem da tabela (gerado por `build.py`; igual à aba `codebook` do `05_kinematics_window.xlsx`).

| column                | description                                                                                                                            | unit / range                          | interpretation / notes                                                           |
|:----------------------|:---------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------|:---------------------------------------------------------------------------------|
| id_match              | Match identifier                                                                                                                       |                                       |                                                                                  |
| id_study              | Participant identifier                                                                                                                 |                                       |                                                                                  |
| day                   | Session: 1 = first assessment (GE and GC), 2 = second assessment (GE only)                                                             | 1-2                                   |                                                                                  |
| moment                | Order of the match within the session                                                                                                  | 1-3                                   |                                                                                  |
| window                | Window index within the match: the match's frames split into 6 equal contiguous blocks                                                 | 1-6                                   | about match duration / 6 each; all frames used                                   |
| phase                 | Window grouped into thirds of the match                                                                                                | early (1-2), middle (3-4), late (5-6) | for the within-match time-course analysis                                        |
| t_start               | Start time of the window from match start                                                                                              | s                                     |                                                                                  |
| t_end                 | End time of the window from match start                                                                                                | s                                     |                                                                                  |
| n_frames              | Tracked frames in the window                                                                                                           | count                                 |                                                                                  |
| dt                    | Time step of the match (same for all its windows)                                                                                      | s                                     |                                                                                  |
| speed_mean_left       | Mean hand speed within the window — left hand                                                                                          | screen units/s                        | higher = faster hand                                                             |
| speed_sd_left         | SD of hand speed within the window — left hand                                                                                         | screen units/s                        | higher = more stop-and-go                                                        |
| path_length_left      | Sum of frame-to-frame displacements within the window — left hand                                                                      | screen units                          | higher = more movement                                                           |
| sparc_left            | Spectral arc length of the window's speed profile (same implementation and 3.0 Hz cutoff as kinematics_match) — left hand              | dimensionless, <= 0                   | closer to 0 = smoother; values are only comparable between windows of this study |
| ldlj_left             | Log dimensionless jerk of the window (T = window duration) — left hand                                                                 | dimensionless, < 0                    | descriptive only, not used for inference (see kinematics_match codebook)         |
| speed_mean_right      | Mean hand speed within the window — right hand                                                                                         | screen units/s                        | higher = faster hand                                                             |
| speed_sd_right        | SD of hand speed within the window — right hand                                                                                        | screen units/s                        | higher = more stop-and-go                                                        |
| path_length_right     | Sum of frame-to-frame displacements within the window — right hand                                                                     | screen units                          | higher = more movement                                                           |
| sparc_right           | Spectral arc length of the window's speed profile (same implementation and 3.0 Hz cutoff as kinematics_match) — right hand             | dimensionless, <= 0                   | closer to 0 = smoother; values are only comparable between windows of this study |
| ldlj_right            | Log dimensionless jerk of the window (T = window duration) — right hand                                                                | dimensionless, < 0                    | descriptive only, not used for inference (see kinematics_match codebook)         |
| speed_mean_bilateral  | Mean hand speed within the window — mean of left and right                                                                             | screen units/s                        | higher = faster hand                                                             |
| speed_sd_bilateral    | SD of hand speed within the window — mean of left and right                                                                            | screen units/s                        | higher = more stop-and-go                                                        |
| path_length_bilateral | Sum of frame-to-frame displacements within the window — mean of left and right                                                         | screen units                          | higher = more movement                                                           |
| sparc_bilateral       | Spectral arc length of the window's speed profile (same implementation and 3.0 Hz cutoff as kinematics_match) — mean of left and right | dimensionless, <= 0                   | closer to 0 = smoother; values are only comparable between windows of this study |
| ldlj_bilateral        | Log dimensionless jerk of the window (T = window duration) — mean of left and right                                                    | dimensionless, < 0                    | descriptive only, not used for inference (see kinematics_match codebook)         |

Notes

- One row per match x window (333 matches x 6 windows = 1998 rows), no missing values. Same source (output/tables/hands_normalized.csv) and same metric functions as kinematics_match.xlsx; only the unit changes from the whole match to short windows. Intended uses: (1) sensitivity of the whole-match result: mean of the windows per match; (2) exploratory within-match time course (phase). The whole-match value is not the mean of the window values.
