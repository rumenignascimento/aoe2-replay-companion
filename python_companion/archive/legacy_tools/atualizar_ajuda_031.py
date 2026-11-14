import ast
import shutil
from datetime import datetime
from pathlib import Path

TOPICOS = [
    ("Comece aqui", """1. Clique em Abrir replay e selecione um arquivo .aoe2record.
2. Para acompanhar novos arquivos, use Pasta savegame.
3. Escolha Todos ou um jogador no filtro da prévia.
4. Ajuste Camadas e informações abaixo do mapa.
5. Configure o overlay à direita e use Testar por 10 segundos.
6. Clique em Salvar configurações para manter seus ajustes.

O botão ? Ajuda fica no cabeçalho. F1 também abre esta janela.
Ctrl + F direciona para a busca. Esc fecha a ajuda."""),

    ("Navegação e aparência", """Visão geral concentra o mapa e o resumo de pedidos.
Overlay reúne os ajustes de sobreposição e do painel.
Minimapa contém os ajustes específicos do mapa.
Ordens apresenta os registros disponíveis.

A faixa de bronze indica a seção selecionada. Nas abas Aparência e Posição, a aba ativa tem filete dourado.

Abrir replay é a ação principal em bronze dourado. Testar por 10 segundos usa bronze mais escuro. As ações secundárias usam ferro escuro.

Ajuda fica somente no cabeçalho. Atalhos e Configurações ficam na base da lateral. Use as barras de rolagem quando os controles não couberem na janela."""),

    ("Replay e monitoramento", """Abrir replay permite selecionar um arquivo existente, inclusive de uma partida em andamento.

Pasta savegame / Alterar pasta inicia o monitoramento da pasta escolhida. Para analisar um arquivo que já estava nela, use Abrir replay.

Confira o perfil correto quando houver várias contas. A detecção automática procura os locais usuais; você pode selecionar a pasta manualmente.

O aplicativo recebe apenas os registros já gravados pelo jogo. Dados mantidos em memória ainda não estarão disponíveis para leitura."""),

    ("Jogadores e contadores", """Todos reúne os participantes. Jogador 1, Jogador 2 etc. filtra as informações daquele jogador. As cores seguem o replay.

Os resumos apresentam pedidos de construção, comandos de produção e solicitações de pesquisa identificados.

Esses números não representam unidades vivas ou construções concluídas. Ordens canceladas ou repetidas podem permanecer na contagem.

A seleção de jogadores no celular é independente da seleção no PC."""),

    ("Overlay: aparência e posição", """Exibir overlay liga ou desliga o minimapa sobre o jogo. A prévia central continua disponível no PC.

Aparência:
Largura altera o tamanho.
Opacidade controla a transparência.

Posição:
Escolha um canto de referência.
Ajuste Margem X e Margem Y pelos campos ou barras deslizantes.
As margens partem do canto escolhido; não são coordenadas absolutas da tela. Os ajustes são aplicados imediatamente.

Testar por 10 segundos permite conferir o resultado fora do jogo e também ativa Exibir overlay.

Ctrl + Alt + M alterna a visibilidade. No uso normal, o overlay acompanha o foco do Age of Empires II DE."""),

    ("Camadas e informações", """Terreno: mostra ou oculta as cores do terreno.
Deslocamentos: mostra ou oculta destinos e rotas solicitadas.
Construções: controla a camada geral de construções e paredes.
Pesquisas e eras: controla a apresentação das solicitações no painel.
Gaia: mostra ou oculta os ícones Gaia identificáveis.

Ocultar militares: esconde ícones de construções militares classificadas.
Ocultar econômicas: esconde ícones de construções econômicas classificadas.
Ocultar casas: esconde os ícones das casas.

Esses filtros não apagam registros nem alteram as contagens. Desligar Construções prevalece sobre os filtros individuais. Tipos sem classificação conhecida podem continuar visíveis.

Quando uma opção Ocultar está ligada, os respectivos ícones ficam escondidos."""),

    ("Ajustes avançados do minimapa", """Na seção Minimapa, ajuste rotação, espelhamento, tamanhos dos ícones e intervalo visível das ordens.

Rotação e espelhamento ajudam a aproximar a orientação da apresentação do jogo.

O intervalo das ordens determina quanto histórico de movimentação aparece no mapa. Ele não controla a velocidade de atualização.

Ícones das fazendas não são apresentados. As casas podem ser ocultadas pela opção correspondente."""),

    ("Rotas e deslocamentos", """As linhas representam destinos solicitados, não trajetos percorridos confirmados.

O leitor trata movimentos pelo terreno e pelo minimapa nos formatos validados com os replays do projeto.

Uma ordem normal substitui a sequência anterior. Ordens enfileiradas com Shift acrescentam destinos identificáveis.

Ícones e números apresentam os tipos e quantidades identificáveis na seleção. Novas unidades podem não ter tipo conhecido.

R indica referência de origem: posição inicial ou destino solicitado anteriormente. Não confirma a posição atual, a saída ou a chegada da tropa."""),

    ("Painel horizontal: Economia e Militar", """O painel horizontal tem duas abas.

Economia reúne construções e solicitações de melhorias econômicas.
Militar reúne construções militares, pedidos de produção e solicitações de melhorias militares.

Avanços de era identificáveis aparecem nas duas abas.

Em Overlay, ajuste visibilidade, largura, posição, margens, tamanho dos ícones e opacidade. Alterne as abas no aplicativo ou use os atalhos configurados.

Os ícones de tecnologias aparecem junto à construção relacionada, com metade do tamanho e em sequência horizontal.

Quando as informações não couberem, use Página anterior e Próxima página.

As quantidades representam pedidos identificados. Não confirmam produção, conclusão, sobrevivência ou destruição."""),

    ("Pesquisas e avanços de era", """Uma ordem de pesquisa identificável pode aparecer com seu ícone junto à construção relacionada.

A associação pode vir do objeto inicial selecionado ou dos metadados disponíveis.

Solicitar uma tecnologia não confirma que ela foi concluída ou que continua em progresso. Cancelamentos podem não ser identificáveis.

Use Pesquisas e eras para controlar essa apresentação no painel."""),

    ("Paliçadas e possíveis aberturas", """Paliçadas iniciais aparecem como linhas sólidas. Trechos solicitados aparecem tracejados.

Bolinhas indicam extremidades sem conexão identificável. São possíveis aberturas, não falhas comprovadas.

A ausência de bolinhas não garante que o muro esteja fechado ou concluído.

A opção de marcar essas extremidades fica na seção Minimapa."""),

    ("Gaia e recursos iniciais", """A camada Gaia mostra objetos neutros identificáveis nos dados iniciais, como animais. Tipos conhecidos usam seu ícone; tipos sem identificação suficiente recebem representação genérica.

Madeira, ouro, pedra, alimentos e relíquias também vêm do mapa inicial.

As quantidades dos agrupamentos Gaia se referem aos objetos iniciais identificados, não aos animais ainda vivos.

A fonte atual não confirma automaticamente quando caças, árvores ou jazidas foram completamente coletadas. Para atualizar sua visualização, use a marcação manual."""),

    ("Marcar recurso esgotado", """1. Clique em Marcar recurso esgotado, abaixo das camadas.
2. Clique próximo ao recurso desejado na prévia do PC.
3. Confira o objeto indicado e confirme a ocultação.

Desfazer reverte a marcação mais recente disponível.
Restaurar marcadores remove as marcações manuais da partida selecionada.

As marcações são salvas por mapa/partida identificado e aplicadas à prévia, ao overlay e à visualização móvel. O arquivo do jogo permanece intacto.

Essa função registra sua observação. Ela não detecta automaticamente o esgotamento. Outros filtros podem continuar ocultando um recurso após restaurar os marcadores."""),

    ("Atalhos de jogadores e painel", """Abra Atalhos na base da lateral. Os valores abaixo são os padrões; os campos mostram as combinações atualmente configuradas.

JOGADORES
Ctrl + Alt + 0: Todos.
Ctrl + Alt + 1 a 8: selecionar jogador.
Ctrl + Alt + seta direita/esquerda: alternar jogador.

PAINEL HORIZONTAL
Ctrl + Alt + E: Economia.
Ctrl + Alt + R: Militar.
Ctrl + Alt + PgUp: página anterior.
Ctrl + Alt + PgDn: próxima página.

Use Aplicar atalhos para testar e Salvar configurações para persistir. Campo vazio desativa o atalho. Combinações ocupadas ou em conflito podem ser recusadas; confira o aviso da interface.

Ctrl + Alt + M é reservado ao overlay.
F1 abre a ajuda com o aplicativo em foco.
Ctrl + F busca dentro da ajuda."""),

    ("Atalhos das camadas", """Combinações padrão:

Ctrl + Alt + Shift + 1: Terreno.
Ctrl + Alt + Shift + 2: Deslocamentos.
Ctrl + Alt + Shift + 3: Construções.
Ctrl + Alt + Shift + 4: Pesquisas e eras.
Ctrl + Alt + Shift + 5: Gaia.
Ctrl + Alt + Shift + 6: Ocultar militares.
Ctrl + Alt + Shift + 7: Ocultar econômicas.
Ctrl + Alt + Shift + 8: Ocultar casas.

Cada combinação inverte o estado da opção. Nos filtros Ocultar, ligado significa esconder os ícones.

Você pode alterar as combinações em Atalhos. Confira os campos atuais: suas configurações salvas podem ser diferentes dos padrões."""),

    ("Celular, tablet e QR Code", """No PC, abra Celular / tablet · QR Code ou use o menu Celular / tablet. Clique em Iniciar / atualizar QR.

Conecte o celular à mesma rede local do PC. O PC pode estar ligado por cabo ao mesmo roteador.

Escaneie o QR Code e abra o endereço no navegador. Se houver vários endereços, escolha o correspondente à rede do celular.

Se o Windows solicitar, permita acesso em redes privadas.

Mantenha o programa aberto no PC. Desligar painel encerra o acesso. Depois de reiniciar, escaneie o novo QR Code.

O painel móvel é uma segunda tela; não envia comandos ao jogo."""),

    ("Zoom por pinça e tela cheia", """No celular, abra dois dedos sobre o mapa para ampliar e aproxime-os para reduzir. Arraste um dedo para deslocar o mapa ampliado. O controle Zoom também permanece disponível.

Minimapa em tela cheia amplia o painel. Use Sair da tela cheia para voltar.

Quando o navegador não permitir tela cheia nativa, o painel ocupa a área disponível da página. Girar o aparelho pode aumentar a área útil.

Fora do mapa, os gestos normais de rolagem continuam disponíveis."""),

    ("Ordens e relatórios", """Ordens mostra os registros disponíveis para o jogador selecionado.

Abrir relatórios abre a pasta dos arquivos gerados. Conforme a análise disponível, podem existir mapas, imagens e registros em JSON ou texto.

Os horários correspondem ao tempo de jogo registrado no replay.

Ausência de informação não significa que o jogador tenha zero unidades ou construções."""),

    ("Salvar, restaurar e atualizar", """Salvar configurações mantém os ajustes disponíveis de mapa, camadas, overlay, painel e atalhos.

Restaurar configurações originais retorna aos padrões e substitui os ajustes personalizados anteriores.

Na versão instalada, os dados ficam em:
%LOCALAPPDATA%/AoE2Overlay

Para atualizar o programa instalado:
1. Aplique o atualizador aos arquivos do projeto.
2. Execute gerar_atualizacao.py com Python 3.12.
3. Informe uma versão superior à última gerada.
4. Feche o aplicativo e execute o novo instalador.

Modificar os arquivos do projeto não modifica automaticamente o executável instalado.

A interface móvel acompanha a versão servida pelo PC. Depois da atualização, reinicie e reconecte pelo novo QR Code."""),

    ("Atualização e desempenho", """Com a atualização contínua aplicada, o próximo ciclo começa quando o anterior termina.

A velocidade depende da leitura, da renderização e da rede. Não há garantia de uma taxa fixa.

O jogo pode gravar os registros em blocos. Consultar mais rapidamente não disponibiliza informações que ainda não foram gravadas.

O intervalo visível das ordens é apenas um filtro do histórico; não é o intervalo de atualização."""),

    ("Resolver problemas", """Mapa vazio:
Abra um replay válido, confirme a pasta e aguarde os dados iniciais ficarem disponíveis.

Interface antiga:
Confirme que o atualizador terminou sem erros. Gere e instale uma nova versão. Verifique se o atalho abre a cópia correta.

Overlay invisível:
Confira Exibir overlay, posição e opacidade. Use Testar por 10 segundos e confira o foco do jogo.

Ícones ausentes:
Confira Construções, Gaia e os filtros Ocultar. Verifique também as marcações manuais de recursos.

Celular sem conexão:
Confira a rede, mantenha o painel ligado e escaneie o QR Code atual. Experimente outro IP listado.

Erro ao iniciar:
Consulte aplicativo.log e falha_inicializacao.log na pasta de dados, quando existirem.

A geração das imagens usa Edge ou Chrome instalado no PC. Ícones ainda indisponíveis podem exigir internet no primeiro download."""),

    ("Limites das informações", """O aplicativo lê o mapa inicial e os comandos gravados no replay. Ele não executa a simulação completa da partida.

Não confirma posições atuais, construções concluídas, tecnologias concluídas, unidades vivas, mortes, conversões, destruições ou recursos restantes.

Contadores representam pedidos identificados. Ordens repetidas ou canceladas podem permanecer na contagem.

As rotas mostram destinos solicitados. As conexões de paliçadas são aproximações.

Ocultar manualmente um recurso é uma anotação do usuário, não uma detecção automática de coleta.

A ausência de um ícone pode resultar dos filtros ativos ou da falta de identificação na fonte."""),
]


def main():
    root = Path(__file__).resolve().parent
    arquivo = root / "ajuda_replay.py"

    if not arquivo.is_file():
        raise RuntimeError(
            "Salve este atualizador na pasta que contém ajuda_replay.py."
        )

    codigo = arquivo.read_text(encoding="utf-8-sig")
    tree = ast.parse(codigo)

    listas = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "TOPICS"
            for target in node.targets
        )
    ]

    if len(listas) != 1:
        raise RuntimeError(
            "Lista TOPICS não reconhecida. Nenhum arquivo foi alterado."
        )

    node = listas[0]
    linhas = codigo.splitlines(keepends=True)

    # Altera somente os tópicos, preservando a interface da Ajuda.
    linhas[node.lineno - 1:node.end_lineno] = [
        "TOPICS = " + repr(TOPICOS) + "\n"
    ]

    atualizado = "".join(linhas)
    ast.parse(atualizado)

    backup = (
        root / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)
    shutil.copy2(arquivo, backup / arquivo.name)

    arquivo.write_text(atualizado, encoding="utf-8")

    print(f"Ajuda atualizada: {len(TOPICOS)} tópicos.")
    print("Backup:", backup)
    print("Agora execute: py -3.12 gerar_atualizacao.py")
    print("Versão sugerida: 0.3.1, ou superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("ERRO:", erro)
        raise SystemExit(1)