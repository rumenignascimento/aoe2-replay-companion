# AoE II · Replay Companion — Python

Refatoração da cópia fornecida pelo proprietário, cuja versão instalada foi informada como **0.4.22**. A próxima versão do projeto é **0.5.0**, definida em `version.json`. Essa versão de código ainda precisa ser compilada e validada no Windows antes de ser instalada ou publicada.

Os módulos de jogo, minimapa, overlays, perfil, idiomas e interface foram preservados. A mudança se concentra na organização e no sistema de distribuição de atualizações.

## O que muda para o comprador

Ao abrir o Companion, uma tarefa em segundo plano consulta a Release estável do canal público. Se houver uma atualização compatível, baixa o pacote e verifica sua assinatura Ed25519 e seu SHA-256. O usuário vê um aviso discreto no Companion, sem abrir sites ou selecionar arquivos, e pode clicar em **Reiniciar e atualizar**.

O aplicador independente aguarda o processo principal fechar, cria backup, substitui os arquivos e reabre o programa. Se a nova versão não confirmar a abertura em45 segundos, tenta restaurar a versão anterior e reabri-la.

A confirmação verifica a criação da janela e a ausência de erros de callbacks de inicialização, não todas as funcionalidades da partida. O renderizador do navegador e um replay real ainda devem ser testados antes de cada publicação.

Sem internet, Release ou download disponível, a janela principal continua funcionando. A consulta automática é limitada a uma por6 horas por instalação; **Verificar agora** consulta imediatamente. O download automático pode ser desativado nas preferências da janela **Atualizações…**.

## Preparação do publicador — uma vez

Extraia esta cópia numa pasta NOVA, mantendo o projeto0.4.22 original como backup. Abra o terminal dentro de `python_companion` e execute:

```bat
py -3.12 preparar_projeto.py
```

Isso cria `.venv`, instala as dependências fixadas e gera uma chave privada fora do projeto, em:

```text
%LOCALAPPDATA%\AoE2CompanionPublisher\keys\ed25519-private.pem
```

Apenas a chave pública é escrita em `companion_updates/trusted_keys.py`. Guarde a chave privada num backup seguro e nunca a envie ao repositório, a compradores ou ao chat. O campo `PUBLIC_KEYS` está vazio nesta entrega: a chave real deve ser criada no seu computador. O build recusa compilar sem essa configuração.

Versione a alteração da chave pública no repositório privado antes de usar a compilação pelo GitHub Actions. Não é necessário instalar chave ou token no computador dos compradores.

## Primeira migração de0.4.22 para0.5.0

O atualizador antigo não conhece o novo protocolo assinado. É necessária UMA atualização inicial pelo fluxo conhecido; depois, as atualizações seguintes poderão ser consultadas e baixadas automaticamente pelo aplicativo.

A opção mais simples para essa migração é gerar o instalador completo, preservando o mesmo AppId e diretório de dados:

```bat
py -3.12 gerar_instalador.py
```

Esse comando usa Python3.12x64 e Inno Setup6 no Windows. Mantém os idiomas e o diretório de configuração `%LOCALAPPDATA%\AoE2Overlay`. Instale com o programa fechado e teste um replay, o overlay e a seleção do perfil.

Se quiser migrar por patch, guarde o build EXATO da0.4.22. Depois de compilar a nova versão, prepare a Release com `--base` e `--base-version 0.4.22`, e aplique esse primeiro patch manualmente usando o aplicador legado de sua cópia anterior. O formato delta1 continua compatível com ele. Não use um build apenas parecido: os hashes precisam corresponder à instalação.

Não distribua uma versão apenas porque compilou; valide no Windows primeiro.

## Compilar e preparar as próximas versões

Mude o número em uma única fonte:

```bat
py -3.12 -m tools.set_version 0.5.1
```

Compile sem Inno Setup e prepare o pacote completo assinado:

```bat
py -3.12 gerar_patch.py
```

Para incluir também um patch menor, passe a pasta do build anterior:

```bat
py -3.12 gerar_patch.py --base "D:\builds\0.5.0\AoE2Overlay"
```

O gerador salva o build em `compilacoes`, registra `ultimo_build_patch.json` e prepara os anexos em `publicacao_github\vVERSAO`. O pacote completo é sempre oferecido como alternativa para instalações sem patch compatível; não é outro instalador e é aplicado automaticamente pelo mesmo atualizador.

Para preparar a Release a partir do último build já compilado, sem recompilar:

```bat
py -3.12 release_github.py
```

Pastas de publicação existentes não são sobrescritas. Para refazer ANTES de publicar, use `--output` com outra pasta. Nunca substitua binários de uma versão já distribuída: crie outra versão.

## Publicar

Canal público: <https://github.com/rumenignascimento/aoe2-companion-updates>.

Crie uma Release **estável**, com tag `vVERSAO`, por exemplo `v0.5.0`. Anexe `updates.json`, `SHA256SUMS.txt` e todos os `.aoe2patch` preparados. Use as notas de `NOTAS_RELEASE.md` após revisar.

O aplicativo consulta:

```text
https://github.com/rumenignascimento/aoe2-companion-updates/releases/latest/download/updates.json
```

Não publique códigos Python, chaves, a pasta de projeto, saves ou diretórios de compilação no canal público. As versões novas usam `updates.json` assinado, não o antigo `atualizacao.json` sem assinatura.

Se tiver GitHub CLI autenticado como publicador:

```bat
py -3.12 release_github.py --upload-draft
```

Essa opção envia SOMENTE um rascunho dos anexos compilados. A publicação continua sob sua revisão no site. Não use o token do publicador no aplicativo.

## Estrutura

- Arquivos Python da raiz: módulos atuais do Companion e wrappers de comandos familiares.
- `companion_updates/`: consulta, verificação de assinatura, download, interface e aplicador independente.
- `tools/`: compilação Windows, assinatura, pacotes e preparação da Release.
- `tests/`: testes de protocolo, integridade, transações, assinatura e interface.
- `archive/legacy_tools/`: atualizadores e backups antigos preservados como histórico. Não fazem parte do build nem são aplicados automaticamente.
- `docs/`: migração, arquitetura, auditoria e validação.
- `icones_aoe2/` e `icone.ico`: recursos fornecidos pelo proprietário, com seus créditos originais.

No repositório privado existente, essa cópia fica em `python_companion/`. A estrutura C# anterior permanece intacta. Os workflows adicionais ficam na `.github/workflows/` da RAIZ do repositório.

## Testar

```bat
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Para abrir o código em desenvolvimento:

```bat
py -3.12 executar_desenvolvimento.py
```

Os testes locais de assinatura, rede simulada, transações e GUI não substituem a compilação e a validação do aplicativo Windows com dados reais. A Release pública não foi alterada nesta entrega.

Leia também `docs/OPERACAO.md`, `docs/ARQUITETURA.md` e `docs/AUDITORIA.md`.
