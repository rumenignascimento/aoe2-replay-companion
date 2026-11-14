# Arquitetura das atualizações

1. O hook `cliente_github_0421.ativar` continua no ponto de entrada existente. Ele delega ao controlador novo, preservando a ordem dos plugins anteriores.
2. Após1,5 segundo, o controlador inicia uma tarefa de consulta. Tk permanece exclusivamente no thread da interface; resultados e progresso passam por fila.
3. `updates.json` da Release estável mais recente contém um envelope assinado Ed25519. A chave pública está fixada no código. Manifestos antigos não assinados são rejeitados.
4. Os metadados declaram versão, URLs HTTPS no canal esperado, tamanho e SHA-256 de cada pacote. Um patch tem fingerprint da base; o pacote completo permite alcançar a versão mais nova sem uma cadeia intermediária obrigatória.
5. `build-info.json` contém a versão real, IDs das chaves públicas compiladas e nomes dos arquivos administrados. O fingerprint continua a verificar hashes dos arquivos, não apenas números digitados.
6. Downloads vão para o diretório de dados, são gravados em arquivo temporário e promovidos só depois de SHA-256/tamanho conferidos. Uma cópia íntegra já baixada é reutilizada. Downloads parciais são descartados e tentados novamente; esta entrega não implementa retomada por HTTP Range.
7. O cliente copia o aplicador integrado para um diretório de execução separado e passa o PID que deve encerrar. O aplicador verifica a assinatura e o hash novamente antes de aplicar.
8. A transação mantém backup/diário, verifica os hashes finais e atualiza o estado instalado. O aplicador reabre o Companion com um token aleatório; a janela confirma sua primeira abertura. Falha ou timeout provoca tentativa de restauração.
9. O publicador prepara somente anexos do diretório de build compilado. A chave privada nunca entra nesse diretório. O upload opcional cria um rascunho no canal público, sem publicá-lo.

## Limites

- O aplicativo continua dependendo do Windows e de um navegador compatível para os recursos existentes. Esta refatoração não substitui o renderizador por outra tecnologia.
- O teste de abertura não é uma validação completa do minimapa, dos replays ou de uma partida em andamento.
- O cache de consultas vale6 horas; atualização imediata pode ser solicitada manualmente.
- Falha de rede não impede usar a versão instalada; não é uma garantia de atualização offline.
- Downgrades automáticos são recusados. Restauração usa o backup local e é uma operação distinta.
- Um formato de pacote futuro exige manter compatibilidade com o aplicador anterior ou distribuir antes um aplicador capaz de lê-lo.
- A primeira transição de0.4.22 exige um instalador/patch inicial pelo fluxo conhecido.
