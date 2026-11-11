# Contrato e modelo matemático — versão 1

## Escopo

O motor reconhece situações em estados de partida fornecidos por um adaptador. Não afirma que uma ordem foi errada, não conhece a intenção do jogador e não prevê o vencedor. A decisão humana pode ter objetivos que não estão representados no estado. Não há detecção de elevação, aprendizado de máquina ou simulador de batalha neste protótipo.

Fluxo: fonte de dados → estados temporais com evidências → métricas → detectores → conclusões e abstenções → CLI/WPF. O núcleo não acessa arquivos, rede ou relógio. Ele pode futuramente ser usado por uma IA de jogo ou por um analisador externo.

## Evidência

Cada medida contém `value`, `origin` e `atSeconds`. A origem pode ser `Observed`, `Reconstructed`, `Simulated` ou `Unknown`. Origem desconhecida, valor nulo ou inválido, instante futuro e evidência com mais de 2 segundos provocam abstenção nos detectores afetados. Isso vale também para perfis de combate: uma tecnologia pode ter mudado os atributos. O adaptador pode emitir um novo registro confirmado do mesmo perfil.

O JSON exige os parâmetros obrigatórios dos construtores; omitir uma coordenada não a transforma em zero. Zero explícito pode ser uma coordenada válida. Evidência simulada só é aceita em documento com `source: Simulated`. Os rótulos de origem são declarações do fornecedor: o motor verifica coerência e tempo, mas não autentica a procedência.

`Reconstructed` significa que o adaptador possui evidência suficiente para reconstruir o campo naquele instante. Não autoriza usar destino de movimento como posição ou completar informação ausente com zero. O contrato atual não carrega uma trilha completa de reconstrução; essa auditoria deverá acompanhar um futuro adaptador real.

`perspective` é obrigatório. Somente `VisibleEnemy` participa dos cálculos militares, mesmo em um documento marcado `Omniscient`; unidades `HiddenEnemy` e de conhecimento desconhecido são ignoradas. Para uma análise da perspectiva do jogador, o adaptador deve derivar a visibilidade real da partida.

`VisibleAreaComplete` confirma que o inventário de inimigos visíveis da região foi fornecido, e não que inexistem ameaças escondidas. O inventário próprio do `GroupId` deve estar completo. Grupos são informados pelo adaptador; a versão 1 não faz agrupamento espacial automático. Outras forças próprias não são tratadas como reforços por proximidade apenas.

Uma unidade conhecida com atributos inválidos causa abstenção militar em vez de ser silenciosamente removida do cálculo. A checagem é conservadora: um inimigo visível inválido mesmo fora da região pode impedir avaliação, porque sua posição pode não ser confiável.

## Força local

Raio padrão R = 18 quadrados ao redor de um centro explicitamente informado. Para cada unidade u de A e cada alvo v de B:

```
armor(v) = armadura corpo a corpo ou à distância, conforme ataque de u
DPS(u,v) = max(1, ataque(u) + bônus(u, classe(v)) - armor(v)) / intervalo(u)
DPS_médio(u,B) = média de DPS(u,v) sobre os alvos de B
P(A,B) = soma de sqrt(HP_atual(u) × DPS_médio(u,B))
razão = P(A,B) / P(B,A)
```

A razão abaixo de 0,80 produz sinal de inferioridade. Comparações estritas de razão usam tolerância absoluta de 1e-9 para evitar alertas no próprio limiar por arredondamento. Não é probabilidade de vitória nem proporção de dano futuro. O índice usa uma aproximação inspirada em modelos de atrito: número de unidades e capacidade de dano/sobrevivência contribuem conjuntamente. Assume unidades capazes de atacar os alvos; não é adequado a monges, curadores, guarnições ou alvos inacessíveis.

O modelo de bônus por classe é simplificado e não equivale às classes de armadura completas do AoE2. O dano mínimo e a agregação também são aproximações; um adaptador não deve apresentar isso como simulação fiel do motor do jogo. Perfis da demonstração são inventados, sem associação ao balanceamento de uma versão real.

Não modela alcance na força, caminhos, tamanho das unidades, bloqueios, área de efeito, foco de fogo, tempos de projétil, recargas já em curso, retirada ou microcontrole. Consequentemente a interface usa o rótulo **heurística não calibrada**, em vez de um percentual de confiança sem base empírica.

## Reforços distantes

Para unidades do mesmo grupo:

```
t(u) = max(0, distância(posição(u), centro) - R) / velocidade(u)
D = unidades com t(u) > 20 segundos
fração_distante = P(D, inimigos_locais) / P(grupo_próprio, inimigos_locais)
```

Sinal se fração_distante ≥ 0,30 e razão local < 1. A métrica de tempo é o menor t entre as unidades distantes. Usa linha reta até a borda da região: obstáculos podem aumentar o tempo real. Não prova que essas unidades receberam ordem de reforçar ou que deveriam se juntar. Grupos separados de propósito devem ter IDs diferentes.

## Capacidade econômica

Para cada recurso r:

```
excesso = soma de max(0, estoque[r] - reserva_planejada[r])
```

Exige excesso ≥ 1000, persistência ≥ 60 segundos, fração de produção ociosa ≥ 0,50 e capacidade de gasto acessível por segundo superior à renda por segundo. Os agregados medem soma nominal de recursos; não representam equivalência de valor entre comida, madeira, ouro e pedra.

O adaptador fornece a reserva por recurso, a persistência com histórico, a renda e a capacidade acessível. Esta última deve considerar receitas de produção/pesquisa pretendidas, edifícios, população disponível, filas e custos acessíveis pela composição atual de recursos. Estoque de madeira não permite assumir que uma unidade que custa ouro pode ser treinada. Zero de reserva só é válido como plano explícito.

O detector alerta para capacidade atual não utilizada. Não recomenda construir mais produção. Uma evolução separada poderá avaliar saturação da produção, necessidade de novos edifícios e comparação de planos.

A persistência fornecida deve se referir ao excesso acima do limiar configurado e da reserva vigente. O motor valida a faixa temporal, mas não a reconstrói a partir dos estados isolados. Alterar os parâmetros exige recalcular esse campo no adaptador.

## Evolução e validação

1. Obter estados reais confiáveis e um catálogo de unidades/tecnologias por versão.
2. Comparar os três detectores com situações anotadas por jogadores; medir falsos positivos e abstenção, além de acertos.
3. Separar conjuntos de calibração e avaliação por partida; não usar o resultado futuro como informação disponível no instante avaliado.
4. Adicionar persistência e agrupamento de ocorrências na linha do tempo. Hoje cada estado é independente e pode gerar sinais repetidos.
5. Introduzir alcance/participação em combate e simulações curtas, com testes contra cenários controlados no jogo.
6. Só então comparar ações alternativas sob objetivos explícitos: atacar, defender, concentrar ou recuar.

As IAs Rehoboam e Charon inspiram categorias de observação e decisões; suas regras não foram importadas e sua força não pode ser deduzida pela quantidade de código.
