# Auditoria da cópia recebida

Origem: ZIP `icones_aoe2.zip` e arquivo `icone.ico` fornecidos pelo proprietário. Versão instalada informada:0.4.22.

O ZIP tinha182 arquivos:99 Python,67 PNG,10 JSON e6 textos. Todos os Python passaram na análise de sintaxe. O grafo de imports a partir de `painel_jogadores` identificou31 módulos locais de execução. Os demais scripts são principalmente atualizadores, ferramentas e cópias de segurança históricas.

Os29 módulos de execução fora do sistema antigo de atualização foram preservados em conteúdo. `docs/runtime_snapshot.json` guarda hashes de texto normalizado (UTF-8, finais de linha LF), conferidos nos testes. Os dois componentes substituídos são o hook de atualizações e o motor de transações, que continua compatível com o formato delta1.

O ícone e os recursos fornecidos foram copiados sem edição. Os créditos dos recursos foram preservados. Não foram incorporados replays, diretórios virtuais de Python, instaladores, compilações ou configurações pessoais.

A organização mantém a implementação Python em uma área própria, sem substituir o projeto C# já existente no repositório privado. Os workflows novos têm nomes próprios para não substituir os pipelines anteriores.

Ainda requer execução no Windows:

- Configuração da chave de assinatura no computador do publicador.
- Compilação dos dois executáveis com PyInstaller e, para a primeira migração, validação do instalador completo.
- Teste funcional com replay, mapa, overlays, painel horizontal, idiomas, seleção de perfil e reinício após atualização.
- Publicação de uma Release estável e teste do fluxo HTTPS real por outro computador.

Nesta entrega, o controlador é testado com rede simulada, assinaturas reais de chaves efêmeras de teste, transações em arquivos de teste e GUI Tk sob display virtual Linux. Nenhuma chave privada real de publicação foi criada ou enviada.
