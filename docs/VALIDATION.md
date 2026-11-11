# Validação do protótipo

Data: 11/11/2026. Ambiente: Debian 13, SDK .NET 10.0.404.

## Confirmado

- Compilação Release de toda a solução, incluindo XAML/WPF por compilação cruzada: **zero erros e zero avisos**.
- **39/39 verificações** do motor passaram. Logs em `docs/logs/`.
- Inferioridade, equilíbrio, superioridade e limite numérico; bônus de contramedida e redução de HP.
- Posição ausente, antiga ou futura; HP desconhecido; perfil antigo; cobertura incompleta; números inválidos.
- Inimigos ocultos não influenciam as métricas; outro grupo não é presumido como reforço.
- Atraso de reforços, velocidade inválida e reforços próximos.
- Capacidade ociosa com excesso persistente, proteção de reserva planejada e abstenção sem plano.
- Ausência de alerta com capacidade abaixo da renda, estoque transitório ou produção ocupada.
- IDs, schema e origens inválidos são rejeitados. Dados marcados simulados não são aceitos em um documento marcado replay.
- JSON incompleto não completa coordenadas com zero.
- Round-trip JSON e determinismo da análise, inclusive ao reordenar estados e unidades.
- CLI: duas execuções independentes lendo `samples/simulated-demo.json` produziram saída idêntica.
- CLI: documento incompleto devolveu código 1 e mensagem em stderr; argumento desconhecido devolveu código 2.

## Saída da demonstração

| Instante | Conclusão |
|---|---|
| 00:10:00 | Inferioridade militar local |
| 00:10:30 | Reforços distantes |
| 00:10:30 | Inferioridade militar local |
| 00:14:00 | Capacidade econômica ociosa |

São 18 avaliações: quatro conclusões, quatro sem sinal e dez sem evidência suficiente. As abstenções são intencionais: estados exclusivamente militares não têm economia, estados exclusivamente econômicos não têm contexto militar e o último estado tem cobertura desconhecida.

Todos os perfis, posições e valores econômicos desse teste são **simulados**. Nenhum evento foi confirmado com replay real. As contagens de regras das IAs enviadas pelo usuário não foram usadas como validação deste motor.

## Reproduzir

```sh
dotnet build AoE2ReplayCompanion.sln -c Release
dotnet run --project checks/Companion.Checks -c Release --no-build
dotnet run --project src/Companion.Cli -c Release --no-build -- samples/simulated-demo.json
```

As verificações são um executável próprio; use `dotnet run`, não `dotnet test`. A configuração de CI incluída repete compilação e verificações em Linux e Windows quando o projeto for publicado no GitHub. O workflow foi escrito, mas não executado no serviço GitHub Actions neste ambiente.

## Resta verificar em Windows

Com SDK .NET 10 instalado:

```powershell
dotnet run --project src/Companion.Wpf -c Release
```

1. Confirmar abertura sem exceção e identificação de dados simulados no topo.
2. Confirmar quatro conclusões em ordem cronológica, instantes e detalhes corretos ao selecionar cada uma.
3. Confirmar leitura completa dos textos, seleção por teclado e rolagem com a janela no tamanho mínimo e em escalas de 100% e 150%.
4. Abrir `samples/simulated-demo.json` e confirmar o mesmo resultado.
5. Exportar o relatório e comparar os dados com `samples/simulated-report.json`.
6. Tentar abrir JSON inválido: deve aparecer mensagem sem encerrar o aplicativo ou substituir o conjunto anterior.
7. Abrir um documento válido que não gere conclusões e confirmar que detalhes antigos não continuam na seleção.

A interface não foi executada neste ambiente Linux. Compilar o WPF aqui confirma compilação de C#/XAML, não comportamento visual ou interativo.

## Limites para validação real

Ainda faltam importação `.aoe2record`, leitura/reconstrução temporal, visibilidade, catálogo de atributos por versão e grupos/plano econômico identificáveis. A entrada JSON é um contrato para adaptadores futuros, não uma validação da origem declarada. Não há demonstração empírica da precisão das recomendações; os limiares ainda precisam de calibração e avaliação independente.
