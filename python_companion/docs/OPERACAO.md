# Operação e recuperação

## Separação de responsabilidades

O código completo e os workflows ficam no repositório PRIVADO. Somente binários compilados e metadados assinados entram nas Releases do repositório PÚBLICO. O GitHub não controla licença de compra: qualquer pessoa pode baixar esses anexos.

A chave privada do publicador fica fora do projeto. Não é criada nem incluída nesta entrega. A chave pública é compilada no aplicativo e no aplicador; nunca é baixada e aceita automaticamente do servidor.

## GitHub Actions

O workflow de testes roda em push/PR na área Python e não usa segredos. O workflow de compilação/publicação é acionado manualmente e usa o ambiente `companion-release`.

Antes de acioná-lo:

1. Execute `preparar_projeto.py` no Windows e registre SOMENTE `companion_updates/trusted_keys.py` no repositório privado.
2. Nas configurações do repositório PRIVADO, crie o ambiente `companion-release`; configure revisores se desejar aprovar o envio.
3. Pelo campo Secrets do GitHub, configure `COMPANION_SIGNING_KEY_PEM` com a chave privada. Não a cole no código, no terminal de CI ou em conversas.
4. Se quiser envio de rascunho automático, configure também `COMPANION_RELEASES_TOKEN`: um token restrito ao repositório PÚBLICO de atualizações, com Contents:write. Alternativamente, use um GitHub App com a mesma permissão.

O `GITHUB_TOKEN` padrão de um repositório privado não ganha acesso de escrita a outro repositório por estar na mesma conta. Por isso, o token dedicado ou o envio manual são necessários.

Os segredos só são expostos aos passos que assinam/enviam o rascunho. O workflow não publica a Release automaticamente. Os anexos ficam também como artefato PRIVADO de CI para revisão.

Há franquias e limites vigentes no GitHub Actions, especialmente em repositórios privados e executores Windows. Não é uma garantia de capacidade ilimitada ou de custo zero para qualquer volume de builds.

## Recuperação

Feche todas as instâncias do Companion antes de restaurar ou aplicar manualmente. Se faltar espaço, o download ou o estágio falham sem converter a instalação em uma versão aprovada.

Os arquivos da instalação que serão alterados são copiados para `.patch_backups`. O diário `.patch_transaction.json` permite recuperar uma substituição interrompida. Não apague backups ou diário enquanto precisar deles.

A restauração manual continua disponível pelo aplicador legado da sua cópia0.4.22, ou pelo módulo `patch_core.rollback` em um ambiente Python de suporte. O cliente novo faz restauração automaticamente quando a confirmação de abertura falha. O monitor não prova que todas as funcionalidades do jogo estão corretas: teste um replay real antes de publicar.

Se houver desligamento abrupto e restar `.patch_lock`, confirme que os aplicadores e o Companion estão fechados e remova SOMENTE esse bloqueio antes de repetir. O aplicador recupera o diário antes de uma nova transação. Esta versão não assume que um bloqueio antigo pode ser removido com segurança enquanto outro processo ainda pode estar trabalhando.

O atualizador é copiado para `%LOCALAPPDATA%\AoE2Overlay\updates\runner` antes de executar. Assim, ele pode atualizar a cópia instalada de si mesmo sem substituí-la enquanto está em execução. Ele recebe apenas caminhos já identificados; o comprador não escolhe pastas ou faz download manual.

## Rotação de chave

Primeiro distribua, assinando com a chave ANTIGA, um aplicativo que confie também na chave NOVA. Só então comece a assinar novas versões com a nova chave. O publicador rejeita builds conhecidos que não confiam na chave usada na Release.

Se perder a única chave privada ou houver comprometimento, pode ser necessária uma migração manual confiável. Não é seguro aceitar uma nova chave pública arbitrária baixada junto do próprio pacote que ela pretende autenticar.

A assinatura Ed25519 autentica os pacotes. Ela não é um certificado Authenticode e não elimina, por si só, avisos SmartScreen do Windows.

## Dados preservados

Configurações, preferências de perfil/idioma, saídas e logs permanecem no diretório de dados existente `%LOCALAPPDATA%\AoE2Overlay`. O atualizador não precisa acessar ou publicar savegames do jogo. As consultas ao GitHub não enviam esses arquivos.

Os ícones e JSON de recursos incluídos no build são sincronizados com o cache de recursos do aplicativo quando mudam; configurações de usuário fora desse cache permanecem intactas. Arquivos extras que não fazem parte dos recursos incluídos são mantidos.

Os arquivos da instalação administrados pelo build são listados em `build-info.json`. Arquivos pessoais extras não são adicionados a um pacote de publicação. Binários do desinstalador não entram nos pacotes de atualização.

A versão instalada efetiva vem de `build-info.json`; nas instalações legadas, pode vir de `.patch_state.json`. Ela não é deduzida do último número compilado. A lista de aplicativos do Windows só muda sua versão registrada quando há execução de um instalador completo.
