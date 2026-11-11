# AoE2 Replay Companion

Protótipo de um motor matemático explicável para reconhecer situações táticas e estratégicas de Age of Empires II. C# / .NET 10, com núcleo independente, CLI e interface WPF.

**Estado: laboratório com dados simulados.** Não lê `.aoe2record`, não executa a IA do jogo e não foi calibrado com partidas reais. O nome descreve o objetivo do projeto. A importação disponível recebe estados JSON, com origem explicitamente declarada.

## Executar

Instale o **SDK .NET 10**. Na raiz:

```sh
dotnet build AoE2ReplayCompanion.sln -c Release
dotnet run --project checks/Companion.Checks -c Release --no-build
dotnet run --project src/Companion.Cli -c Release --no-build -- --demo
```

A CLI e as verificações funcionam em Linux e Windows. O projeto WPF permite compilação cruzada, mas a interface só executa em Windows:

```powershell
dotnet run --project src/Companion.Wpf -c Release
```

Na interface: carregue a demonstração, selecione uma conclusão na linha do tempo e consulte suas métricas, evidências e hipóteses. É possível abrir estados JSON e exportar o relatório. Não existe reprodução ou navegação em replay real.

## Analisar seus próprios estados

Use o arquivo de exemplo como contrato inicial:

```sh
dotnet run --project src/Companion.Cli -- --write-demo samples/my-demo.json
dotnet run --project src/Companion.Cli -- samples/my-demo.json
```

A saída da análise é JSON em stdout e pode ser redirecionada para um arquivo. Erros vão para stderr, com código de saída diferente de zero. `--write-demo` sobrescreve o caminho informado.

O documento exige `schemaVersion: 1`, `datasetId`, `source`, `perspective` e `snapshots`. Os campos obrigatórios não recebem valores padrão silenciosos quando omitidos no JSON. Use `null` para evidências indisponíveis. Valores de enum são strings. `Unknown` não é uma origem válida para um documento analisável.

## Primeiros temas

| Código | Tema | Critério padrão |
|---|---|---|
| `TACTICAL_LOCAL_INFERIORITY` | Superioridade militar local | Índice próprio / inimigo visível < 0,80 |
| `TACTICAL_DELAYED_REINFORCEMENTS` | Concentração do exército | Grupo local em inferioridade e pelo menos 30% da força do mesmo grupo a mais de 20 s da área |
| `STRATEGIC_IDLE_CAPACITY` | Uso da capacidade econômica | Excesso ≥ 1000 por ≥ 60 s, produção ≥ 50% ociosa e capacidade acessível de gasto maior que renda |

Os limiares são configuráveis via `AnalysisOptions`. São escolhas iniciais de engenharia, não valores empiricamente validados. A força inclui HP atual, ataque, intervalo de ataque, armadura correspondente e bônus por classe. Alcance e movimento durante combate ainda não entram nesse índice.

Cada avaliação retorna uma conclusão, ausência de sinal ou **evidência insuficiente**. Cada conclusão inclui instante, jogador, código, métricas, unidades participantes, origem do conjunto e explicações. Conclusões são ordenadas por instante, estado e código. A repetição dos mesmos dados produz o mesmo relatório, independentemente da ordem de entrada dos estados.

A demonstração gera quatro conclusões: inferioridade em 10:00; inferioridade e reforços distantes em 10:30; capacidade ociosa em 14:00. Também contém equilíbrio, uma reserva econômica intencional e cobertura desconhecida, para demonstrar ausência de sinal e abstenção.

## Organização

- `src/Companion.Core`: modelos, evidências, parâmetros e motor. Sem dependência de WPF ou formato de replay.
- `src/Companion.Scenarios`: perfis e estados inventados, explicitamente simulados.
- `src/Companion.Cli`: leitura de estados JSON e saída de diagnóstico.
- `src/Companion.Wpf`: linha do tempo, detalhes, abertura de JSON e exportação.
- `checks/Companion.Checks`: verificações executáveis, sem bibliotecas externas de teste.
- `samples`: entrada e relatório de demonstração.
- `docs/ENGINE.md`: fórmulas, contratos e limitações.
- `docs/VALIDATION.md`: resultados e roteiro de validação em Windows.

A solução não depende dos scripts enviados de Rehoboam ou Charon. Seus arquivos não foram copiados para o projeto; não há necessidade de instalá-los para executar o protótipo.

## Próxima integração

Precisamos de uma fonte de estados temporais confiáveis. Um adaptador de replay deverá identificar a versão da partida e informar explicitamente quais campos consegue ler ou reconstruir. A API atual recebe estados completos; não reconstrói posições a partir de destinos ou posições iniciais.

Antes de habilitar dados reais, será necessário mapear unidades e tecnologias para perfis versionados do jogo, validar visibilidade, formar grupos com critérios explícitos e reconstruir economia com histórico. Campos indisponíveis devem causar abstenção. Consulte `docs/ENGINE.md`.

Este é um repositório Git local, sem remoto publicado. Após extrair o ZIP de código-fonte, execute `git init -b main` para iniciar seu próprio histórico, caso não esteja trabalhando no repositório já inicializado no ambiente. A publicação no GitHub pode ser feita posteriormente na conta escolhida pelo proprietário.
