# Plano de análise

Desenho da análise, na ordem em que entra no artigo. As tabelas são as desta pasta (`01` a `05` e `09`); cada uma tem um `.md` com o significado das colunas. Decisões ainda em aberto estão marcadas como **\[a decidir\]** e são do estatístico; o resto está definido.

## Perguntas

1. **Entre grupos (dia 1):** crianças e adolescentes com TEA (GE, n \= 38\) diferem dos controles pareados por sexo e idade (GC, n \= 38\) no desempenho num jogo de rastreamento de mãos e na suavidade do movimento das mãos?  
2. **Dentro do GE (dia 1 → dia 2):** o desempenho e a suavidade do GE mudam entre a primeira sessão e a segunda, cerca de 3,5 meses depois (n \= 36 com as duas)?

O GC não tem dia 2 (desenho do estudo), então a pergunta 2 não tem comparador controle: é uma comparação pré/pós intra-sujeito, e a mudança pode refletir prática, maturação ou a intervenção. Isso deve ser declarado como limitação.

## Desfechos

| Papel | Desfecho | Tabela | Unidade |
| :---- | :---- | :---- | :---- |
| Primário 1 | `hit_rate` (via `n_hits` / `n_balls`) | 03\_matches | partida |
| Primário 2 | `reaction_time_median` | 03\_matches | partida |
| Primário 3 | `sparc_bilateral` | 04\_kinematics\_match | partida |
| Secundário | `speed_mean_bilateral`, `path_length_bilateral` (quantidade de movimento) | 04\_kinematics\_match | partida |
| Sensibilidade | média das 6 janelas de `sparc_bilateral` | 05\_kinematics\_window | partida |
| Exploratório | `sparc_bilateral` por fase (early / middle / late) | 05\_kinematics\_window | janela |
| Usabilidade | `sus` (escore 0-100) | 09\_sus | participante |
| Só descritivo | `ldlj_*`, `speed_sd_*`, `traj_corr_*`, `mirror_score`; `reaction_time_mean/sd/q1/q3/iqr`; `distance_*` | 03, 04 | partida |

Por que o SPARC e não o LDLJ: sobre partidas inteiras o LDLJ acompanha a quantidade de movimento (ρ \= −0,86 com velocidade média, −0,88 com comprimento do trajeto) e não a suavidade; o SPARC normaliza a forma do perfil de velocidade. Isso importa ainda mais aqui, porque o GE se move muito mais que o GC (velocidade mediana 0,77 vs 0,44 telas/s): o LDLJ só reproduziria essa diferença. Detalhes em `04_kinematics_match.md`.

Por que `speed_mean` e `path_length` são secundários e não só descritivos: a diferença de quantidade de movimento entre grupos é grande e tem leitura própria (vigor, agitação motora, estratégia de varredura) e ajuda a interpretar o SPARC.

## Fatores e covariáveis

- `group` (GE / GC): fator principal da pergunta 1\.  
- `day` (1 / 2): fator da pergunta 2, só no GE.  
- `match_number`(1-3): partida dentro da sessão. Entra em todos os modelos por partida como efeito fixo, com a interação com o fator principal (`group × moment` ou `day × moment`): a evolução dentro da sessão difere por grupo / por dia?  
- `sex` e `age` **não entram** como covariáveis na pergunta 1: são variáveis de pareamento (idênticas entre grupos). **\[a decidir\]** se `age` entra como covariável na pergunta 2 (faixa larga, 5-24 anos) ou como moderador exploratório.  
- Sem subgrupos diagnósticos: a única classificação do estudo é TEA confirmado pela CARS-2 (todos os GE). Comorbidades não entram.  
- Nível do jogo: não está disponível (registros incorretos no banco). `n_balls` (66 ou 78\) é absorvido ao modelar `n_hits` em `n_balls`.

## 1\. Descrição

Tabela 1 (pronta: `02_cohort`): idade, sexo e partidas válidas por grupo. Descritivas de todos os desfechos por grupo × dia × partida: média (DP); mediana \[Q1, Q3\]; n. A figura `08_outcomes_by_group.png` mostra os três primários nessa estrutura (média ± IC 95%).

## 2\. Análise A: GE vs GC no dia 1 (modelos mistos por partida)

Só partidas com `day = 1` (GE 112, GC 114). Cada participante tem 2-3 partidas; participante entra como intercepto aleatório (`(1 | id_study)`). Juntar `03_matches` ou `04_kinematics_match` com `01_participants` por `id_study` para obter `group`.

| Desfecho | Modelo | Efeitos fixos |
| :---- | :---- | :---- |
| `hit_rate` | GLMM binomial, resposta `cbind(n_hits, n_balls − n_hits)` | `group × moment` |
| `reaction_time_median` | LMM; log se os resíduos forem assimétricos | `group × moment` |
| `sparc_bilateral` | LMM | `group × moment` |

- `hit_rate` tem teto (quartil superior 0,92; GC mediana 0,86-0,89): esperar sobredispersão no binomial. **\[a decidir\]** beta-binomial, efeito aleatório por observação, ou LMM na proporção como alternativa declarada.  
- Interação: testar `group × moment`; se não significativa, reportar o modelo só com efeitos principais.  
- Reportar: médias marginais por grupo e partida, diferença GE − GC com IC 95%, tamanho de efeito padronizado, p.  
- Pareamento: os pares GE-GC não estão identificados na tabela (o pareamento foi feito no recrutamento, por sexo e idade). A análise trata os grupos como independentes; **\[a decidir\]** se vale a pena recuperar os pares para um modelo pareado.  
- Multiplicidade: três co-primários. Sugerido: correção de Holm dentro da família. **\[a decidir\]** Holm ou co-primários declarados sem correção; registrar antes de rodar.

## 3\. Análise B: GE, dia 1 vs dia 2 (modelos mistos por partida)

Só GE (dia 1: 112 partidas, 38 participantes; dia 2: 107, 36). Participante como intercepto aleatório; **\[a decidir\]** intercepto aleatório de sessão dentro de participante (`(1 | id_study / day)`) dado que há 3 partidas por sessão.

| Desfecho | Modelo | Efeitos fixos |
| :---- | :---- | :---- |
| `hit_rate` | GLMM binomial | `day × moment` |
| `reaction_time_median` | LMM (log se preciso) | `day × moment` |
| `sparc_bilateral` | LMM | `day × moment` |

- Os 2 participantes sem dia 2 entram com o dia 1 (o modelo misto lida com o desbalanço); alternativa de sensibilidade: só os 36 com as duas sessões.  
- Descritivamente, do dia 1 para o dia 2 o GE acelera (tempo de reação mediano 1,7 → 1,4 s), fica um pouco mais suave (SPARC −9,2 → −8,9) e o acerto não muda na média, mas cai ao longo das partidas do dia 2 (0,86 → 0,77). A interação `day × moment` é, portanto, de interesse, não só o efeito principal.  
- Reportar: médias marginais por dia e partida, diferença dia 2 − dia 1 com IC 95%, tamanho de efeito, p. Mesma regra de multiplicidade da análise A.

## 4\. Sensibilidade (mesmos modelos, sem resultado próprio)

1. **Janelas:** média das 6 janelas de `sparc_bilateral` por partida (`05_kinematics_window`), no mesmo modelo do primário 3, nas análises A e B. O resultado se mantém com unidade de 12 s em vez de 70 s? Comparar direção e efeito padronizado, não a diferença bruta (escalas diferem: ≈ −9,3 vs. ≈ −4,7).  
2. **Quantidade de movimento como covariável:** o SPARC é desenhado para não depender da quantidade de movimento, mas a diferença entre grupos é grande. Repetir o modelo do SPARC com `path_length_bilateral` como covariável, para mostrar que a diferença de suavidade (se houver) não é só a de movimento. **\[a decidir\]** se entra como sensibilidade ou se basta o argumento metodológico.  
3. **Taxa de amostragem:** 13 partidas do GC estão em 6,3-6,7 Hz (os demais 8-9,6 Hz). Repetir a análise A do SPARC sem essas 13 partidas (ou com `n_frames` como covariável).

## 5\. Secundário

- `speed_mean_bilateral` e `path_length_bilateral` nos mesmos modelos das análises A e B (LMM, log se preciso). Pergunta: o GE se move mais/mais rápido que o GC? Isso muda no dia 2?  
- **Suavidade e desempenho dentro do jogo** (opcional): `hit_rate ~ sparc_bilateral + group + moment + (1 | id_study)`, por partida, dia 1\. Liga as duas famílias primárias.

## 6\. Exploratório: curso temporal dentro da partida

`sparc_bilateral ~ group × phase + moment + (1 | id_study / id_match)`, com janela aninhada em partida aninhada em participante (`05_kinematics_window`), dia 1\. Interesse: interação `group × phase` (fadiga ou aquecimento diferentes por grupo). Ressalva: as janelas 1 e 6 são sistematicamente mais suaves e mais lentas (início antes de as mãos entrarem em ação; fim depois da última bolha).

Não fazer média das janelas por participante: perde a hierarquia e apaga a fase.

## 6b. Usabilidade (SUS)

Uma medida por participante (`09_sus`), respondida ao fim da última sessão: GC no dia 1, GE no dia 2 (36) ou no dia 1 (2). A criança respondeu com ajuda do pesquisador e do profissional da APAE.

- **Descritivo:** escore por grupo, mediana \[Q1, Q3\] e média (DP); proporção ≥ 68\. Pronto na aba `descriptives` da `09_sus.xlsx`: GE 85,0 \[75,6; 87,5\], GC 85,0 \[77,5; 87,5\].  
- **GE vs GC:** Mann-Whitney (efeito teto, assimetria à esquerda), com diferença de medianas (Hodges-Lehmann) e IC 95%. Fora da família dos co-primários.  
- **Opcional, exploratório:** relação entre `sus` e o desempenho da última sessão (por exemplo, `hit_rate` médio das partidas do `sus_day`), Spearman por grupo.

## 7\. Checagens e limitações a declarar

- Resíduos dos modelos mistos; transformação log do tempo de reação se necessário.  
- n \= 38 por grupo e 36 no pré/pós: poder limitado para interações.  
- Sem grupo controle no dia 2: a mudança do GE não separa prática, maturação e intervenção.  
- Faixa etária larga (5-24 anos) nos dois grupos; o pareamento garante o equilíbrio, não a homogeneidade.  
- SPARC calculado sobre a partida inteira não é comparável a limiares publicados (que usam gestos isolados); comparações só dentro do estudo. Corte de 3,0 Hz imposto pela amostragem.  
- Rastreio por webcam a 6-10 Hz, 2D, sem filtro prévio: limitação do dispositivo (detalhes em `04_kinematics_match.md`).  
- Nível do jogo indisponível; as partidas de uma mesma sessão podem ter tido configurações diferentes, e isso não é modelável.  
- SUS: texto adaptado para crianças (itens 5 e 6 com conteúdo diferente do original) e resposta assistida; comparação com a referência 68 só com cautela.  
- Acoplamento entre mãos (`traj_corr_*`, `mirror_score`): a tarefa separa as mãos por desenho; **\[a decidir\]** se entram como descritivos ou ficam fora do artigo.

## 8\. Figuras e tabelas previstas

- Fig. 1: fluxo da amostra (pronta: `07_consort_flow`).  
- Fig. 2: os três primários por grupo × dia × partida (versão descritiva pronta: `08_outcomes_by_group.png`; versão final com médias marginais dos modelos).  
- Fig. 3 (opcional): SPARC por fase e grupo.  
- Tabela 1: amostra (pronta: `02_cohort`). Tabela 2: análise A (GE vs GC). Tabela 3: análise B (dia 1 vs dia 2 no GE). Tabela 4 (opcional): secundários e sensibilidade.

## Resumo para o Methods

Modelos mistos por partida para os três desfechos primários (taxa de acerto, tempo de reação, suavidade pelo SPARC), com participante como efeito aleatório e partida dentro da sessão como covariável: (A) grupo × partida no dia 1, GE vs controles pareados; (B) dia × partida no GE, primeira vs segunda sessão. Janelas de 12 s, quantidade de movimento e taxa de amostragem como sensibilidade; LDLJ reportado descritivamente; velocidade e comprimento do trajeto como desfechos secundários; curso temporal da suavidade dentro da partida como análise exploratória. Usabilidade pelo SUS, respondido ao fim da última sessão, descrita por grupo e comparada por Mann-Whitney.