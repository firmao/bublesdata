# Tabela `09_sus`

Uma linha por participante, n \= 76 (38 GE, 38 GC): as 10 respostas do System Usability Scale (SUS) e o escore. Respondido uma vez, ao fim da última partida da última sessão do participante, pela própria criança com ajuda do pesquisador e do profissional da APAE.

## Resultado

|  | Todos (n \= 76\) | GE (n \= 38\) | GC (n \= 38\) |
| :---- | :---- | :---- | :---- |
| Média (DP) | 81,3 (10,4) | 80,8 (11,6) | 81,8 (9,2) |
| Mediana \[Q1, Q3\] | 85,0 \[77,5; 87,5\] | 85,0 \[75,6; 87,5\] | 85,0 \[77,5; 87,5\] |
| Mín-máx | 52,5-100 | 55,0-100 | 52,5-95,0 |
| Escore ≥ 68 | 87% | 82% | 92% |

## Codebook

| column | description | scale / range | computation / direction | notes |
| :---- | :---- | :---- | :---- | :---- |
| id\_study | Participant identifier; key to the other tables |  |  |  |
| group | GE \= autism spectrum disorder (CARS-2); GC \= matched control | GE / GC |  |  |
| sus\_day | Session at whose end the SUS was answered: the participant's last session | 1-2 | GC: always 1\. GE: 2, or 1 for the 2 participants without day 2 (229, 313\) |  |
| sus\_1 | I would play this game more times \[applied: "Eu usaria este jogo mais vezes?"\] | 1 (strongly disagree) \- 5 (strongly agree) | positive item | raw item, not reversed |
| sus\_2 | The game was too complicated \[applied: "O jogo era complicado demais?"\] | 1 (strongly disagree) \- 5 (strongly agree) | negative item (higher \= worse) | raw item, not reversed |
| sus\_3 | I found the game easy to use \[applied: "Eu achei o jogo fácil de usar?"\] | 1 (strongly disagree) \- 5 (strongly agree) | positive item | raw item, not reversed |
| sus\_4 | I need someone helping me to use this game \[applied: "Eu preciso de alguém me ajudando a usar este jogo?"\] | 1 (strongly disagree) \- 5 (strongly agree) | negative item (higher \= worse) | raw item, not reversed |
| sus\_5 | I understood the game (how to score points, when I missed, the game score: integrated game functions) \[applied: "Eu entendi o jogo (como ganhar pontos. quando errava, a pontuação do jogo (funções do jogo integradas))?"\] | 1 (strongly disagree) \- 5 (strongly agree) | positive item | raw item, not reversed |
| sus\_6 | I found it complicated to understand the information on the screen (score, direction to hit the ball, time) \[applied: "Eu achei complicado entender as informações na tela (pontuação, direção para lançar a bola, tempo e pontuação)."\] | 1 (strongly disagree) \- 5 (strongly agree) | negative item (higher \= worse) | raw item, not reversed |
| sus\_7 | I believe other children will find it easy to learn to play \[applied: "Eu acredito que outras crianças terão facilidade em aprender a jogar?"\] | 1 (strongly disagree) \- 5 (strongly agree) | positive item | raw item, not reversed |
| sus\_8 | I found the game very complicated to use \[applied: "Eu achei o jogo muito complicado de usar?"\] | 1 (strongly disagree) \- 5 (strongly agree) | negative item (higher \= worse) | raw item, not reversed |
| sus\_9 | I felt very confident using this game \[applied: "Eu me senti muito confiante em usar este jogo?"\] | 1 (strongly disagree) \- 5 (strongly agree) | positive item | raw item, not reversed |
| sus\_10 | I needed to learn many things to use this game \[applied: "Eu precisei aprender muitas coisas para usar esse jogo?"\] | 1 (strongly disagree) \- 5 (strongly agree) | negative item (higher \= worse) | raw item, not reversed |
| sus | System Usability Scale score | 0-100 | \[sum(odd item \- 1\) \+ sum(5 \- even item)\] x 2.5 | higher \= more usable |

&nbsp;