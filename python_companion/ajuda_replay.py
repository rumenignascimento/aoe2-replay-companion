import tkinter as tk
from tkinter import ttk
import unicodedata
from central_replay import BG, CARD, EDGE, TEXT, MUTED
ACCENT = '#e0b56c'
TOPICS = [('Comece aqui', '1. Clique em Abrir replay e selecione um arquivo .aoe2record.\n2. Para acompanhar novos arquivos, use Pasta savegame.\n3. Escolha Todos ou um jogador no filtro da prévia.\n4. Ajuste Camadas e informações abaixo do mapa.\n5. Configure o overlay à direita e use Testar por 10 segundos.\n6. Clique em Salvar configurações para manter seus ajustes.\n\nO botão ? Ajuda fica no cabeçalho. F1 também abre esta janela.\nCtrl + F direciona para a busca. Esc fecha a ajuda.'), ('Navegação e aparência', 'Visão geral concentra o mapa e o resumo de pedidos.\nOverlay reúne os ajustes de sobreposição e do painel.\nMinimapa contém os ajustes específicos do mapa.\nOrdens apresenta os registros disponíveis.\n\nA faixa de bronze indica a seção selecionada. Nas abas Aparência e Posição, a aba ativa tem filete dourado.\n\nAbrir replay é a ação principal em bronze dourado. Testar por 10 segundos usa bronze mais escuro. As ações secundárias usam ferro escuro.\n\nAjuda fica somente no cabeçalho. Atalhos e Configurações ficam na base da lateral. Use as barras de rolagem quando os controles não couberem na janela.'), ('Replay e monitoramento', 'Abrir replay permite selecionar um arquivo existente, inclusive de uma partida em andamento.\n\nPasta savegame / Alterar pasta inicia o monitoramento da pasta escolhida. Para analisar um arquivo que já estava nela, use Abrir replay.\n\nConfira o perfil correto quando houver várias contas. A detecção automática procura os locais usuais; você pode selecionar a pasta manualmente.\n\nO aplicativo recebe apenas os registros já gravados pelo jogo. Dados mantidos em memória ainda não estarão disponíveis para leitura.'), ('Jogadores e contadores', 'Todos reúne os participantes. Jogador 1, Jogador 2 etc. filtra as informações daquele jogador. As cores seguem o replay.\n\nOs resumos apresentam pedidos de construção, comandos de produção e solicitações de pesquisa identificados.\n\nEsses números não representam unidades vivas ou construções concluídas. Ordens canceladas ou repetidas podem permanecer na contagem.\n\nA seleção de jogadores no celular é independente da seleção no PC.'), ('Overlay: aparência e posição', 'Exibir overlay liga ou desliga o minimapa sobre o jogo. A prévia central continua disponível no PC.\n\nAparência:\nLargura altera o tamanho.\nOpacidade controla a transparência.\n\nPosição:\nEscolha um canto de referência.\nAjuste Margem X e Margem Y pelos campos ou barras deslizantes.\nAs margens partem do canto escolhido; não são coordenadas absolutas da tela. Os ajustes são aplicados imediatamente.\n\nTestar por 10 segundos permite conferir o resultado fora do jogo e também ativa Exibir overlay.\n\nCtrl + Alt + M alterna a visibilidade. No uso normal, o overlay acompanha o foco do Age of Empires II DE.'), ('Camadas e informações', 'Terreno: mostra ou oculta as cores do terreno.\nDeslocamentos: mostra ou oculta destinos e rotas solicitadas.\nConstruções: controla a camada geral de construções e paredes.\nPesquisas e eras: controla a apresentação das solicitações no painel.\nGaia: mostra ou oculta os ícones Gaia identificáveis.\n\nOcultar militares: esconde ícones de construções militares classificadas.\nOcultar econômicas: esconde ícones de construções econômicas classificadas.\nOcultar casas: esconde os ícones das casas.\n\nEsses filtros não apagam registros nem alteram as contagens. Desligar Construções prevalece sobre os filtros individuais. Tipos sem classificação conhecida podem continuar visíveis.\n\nQuando uma opção Ocultar está ligada, os respectivos ícones ficam escondidos.'), ('Ajustes avançados do minimapa', 'Na seção Minimapa, ajuste rotação, espelhamento, tamanhos dos ícones e intervalo visível das ordens.\n\nRotação e espelhamento ajudam a aproximar a orientação da apresentação do jogo.\n\nO intervalo das ordens determina quanto histórico de movimentação aparece no mapa. Ele não controla a velocidade de atualização.\n\nÍcones das fazendas não são apresentados. As casas podem ser ocultadas pela opção correspondente.'), ('Rotas e deslocamentos', 'As linhas representam destinos solicitados, não trajetos percorridos confirmados.\n\nO leitor trata movimentos pelo terreno e pelo minimapa nos formatos validados com os replays do projeto.\n\nUma ordem normal substitui a sequência anterior. Ordens enfileiradas com Shift acrescentam destinos identificáveis.\n\nÍcones e números apresentam os tipos e quantidades identificáveis na seleção. Novas unidades podem não ter tipo conhecido.\n\nR indica referência de origem: posição inicial ou destino solicitado anteriormente. Não confirma a posição atual, a saída ou a chegada da tropa.'), ('Painel horizontal: Economia e Militar', 'O painel horizontal tem duas abas.\n\nEconomia reúne construções e solicitações de melhorias econômicas.\nMilitar reúne construções militares, pedidos de produção e solicitações de melhorias militares.\n\nAvanços de era identificáveis aparecem nas duas abas.\n\nEm Overlay, ajuste visibilidade, largura, posição, margens, tamanho dos ícones e opacidade. Alterne as abas no aplicativo ou use os atalhos configurados.\n\nOs ícones de tecnologias aparecem junto à construção relacionada, com metade do tamanho e em sequência horizontal.\n\nQuando as informações não couberem, use Página anterior e Próxima página.\n\nAs quantidades representam pedidos identificados. Não confirmam produção, conclusão, sobrevivência ou destruição.'), ('Pesquisas e avanços de era', 'Uma ordem de pesquisa identificável pode aparecer com seu ícone junto à construção relacionada.\n\nA associação pode vir do objeto inicial selecionado ou dos metadados disponíveis.\n\nSolicitar uma tecnologia não confirma que ela foi concluída ou que continua em progresso. Cancelamentos podem não ser identificáveis.\n\nUse Pesquisas e eras para controlar essa apresentação no painel.'), ('Paliçadas e possíveis aberturas', 'Paliçadas iniciais aparecem como linhas sólidas. Trechos solicitados aparecem tracejados.\n\nBolinhas indicam extremidades sem conexão identificável. São possíveis aberturas, não falhas comprovadas.\n\nA ausência de bolinhas não garante que o muro esteja fechado ou concluído.\n\nA opção de marcar essas extremidades fica na seção Minimapa.'), ('Gaia e recursos iniciais', 'A camada Gaia mostra objetos neutros identificáveis nos dados iniciais, como animais. Tipos conhecidos usam seu ícone; tipos sem identificação suficiente recebem representação genérica.\n\nMadeira, ouro, pedra, alimentos e relíquias também vêm do mapa inicial.\n\nAs quantidades dos agrupamentos Gaia se referem aos objetos iniciais identificados, não aos animais ainda vivos.\n\nA fonte atual não confirma automaticamente quando caças, árvores ou jazidas foram completamente coletadas. Para atualizar sua visualização, use a marcação manual.'), ('Marcar recurso esgotado', '1. Clique em Marcar recurso esgotado, abaixo das camadas.\n2. Clique próximo ao recurso desejado na prévia do PC.\n3. Confira o objeto indicado e confirme a ocultação.\n\nDesfazer reverte a marcação mais recente disponível.\nRestaurar marcadores remove as marcações manuais da partida selecionada.\n\nAs marcações são salvas por mapa/partida identificado e aplicadas à prévia, ao overlay e à visualização móvel. O arquivo do jogo permanece intacto.\n\nEssa função registra sua observação. Ela não detecta automaticamente o esgotamento. Outros filtros podem continuar ocultando um recurso após restaurar os marcadores.'), ('Atalhos de jogadores e painel', 'Abra Atalhos na base da lateral. Os valores abaixo são os padrões; os campos mostram as combinações atualmente configuradas.\n\nJOGADORES\nCtrl + Alt + 0: Todos.\nCtrl + Alt + 1 a 8: selecionar jogador.\nCtrl + Alt + seta direita/esquerda: alternar jogador.\n\nPAINEL HORIZONTAL\nCtrl + Alt + E: Economia.\nCtrl + Alt + R: Militar.\nCtrl + Alt + PgUp: página anterior.\nCtrl + Alt + PgDn: próxima página.\n\nUse Aplicar atalhos para testar e Salvar configurações para persistir. Campo vazio desativa o atalho. Combinações ocupadas ou em conflito podem ser recusadas; confira o aviso da interface.\n\nCtrl + Alt + M é reservado ao overlay.\nF1 abre a ajuda com o aplicativo em foco.\nCtrl + F busca dentro da ajuda.'), ('Atalhos das camadas', 'Combinações padrão:\n\nCtrl + Alt + Shift + 1: Terreno.\nCtrl + Alt + Shift + 2: Deslocamentos.\nCtrl + Alt + Shift + 3: Construções.\nCtrl + Alt + Shift + 4: Pesquisas e eras.\nCtrl + Alt + Shift + 5: Gaia.\nCtrl + Alt + Shift + 6: Ocultar militares.\nCtrl + Alt + Shift + 7: Ocultar econômicas.\nCtrl + Alt + Shift + 8: Ocultar casas.\n\nCada combinação inverte o estado da opção. Nos filtros Ocultar, ligado significa esconder os ícones.\n\nVocê pode alterar as combinações em Atalhos. Confira os campos atuais: suas configurações salvas podem ser diferentes dos padrões.'), ('Celular, tablet e QR Code', 'No PC, abra Celular / tablet · QR Code ou use o menu Celular / tablet. Clique em Iniciar / atualizar QR.\n\nConecte o celular à mesma rede local do PC. O PC pode estar ligado por cabo ao mesmo roteador.\n\nEscaneie o QR Code e abra o endereço no navegador. Se houver vários endereços, escolha o correspondente à rede do celular.\n\nSe o Windows solicitar, permita acesso em redes privadas.\n\nMantenha o programa aberto no PC. Desligar painel encerra o acesso. Depois de reiniciar, escaneie o novo QR Code.\n\nO painel móvel é uma segunda tela; não envia comandos ao jogo.'), ('Zoom por pinça e tela cheia', 'No celular, abra dois dedos sobre o mapa para ampliar e aproxime-os para reduzir. Arraste um dedo para deslocar o mapa ampliado. O controle Zoom também permanece disponível.\n\nMinimapa em tela cheia amplia o painel. Use Sair da tela cheia para voltar.\n\nQuando o navegador não permitir tela cheia nativa, o painel ocupa a área disponível da página. Girar o aparelho pode aumentar a área útil.\n\nFora do mapa, os gestos normais de rolagem continuam disponíveis.'), ('Ordens e relatórios', 'Ordens mostra os registros disponíveis para o jogador selecionado.\n\nAbrir relatórios abre a pasta dos arquivos gerados. Conforme a análise disponível, podem existir mapas, imagens e registros em JSON ou texto.\n\nOs horários correspondem ao tempo de jogo registrado no replay.\n\nAusência de informação não significa que o jogador tenha zero unidades ou construções.'), ('Salvar, restaurar e atualizar', 'Salvar configurações mantém os ajustes disponíveis de mapa, camadas, overlay, painel e atalhos.\n\nRestaurar configurações originais retorna aos padrões e substitui os ajustes personalizados anteriores.\n\nNa versão instalada, os dados ficam em:\n%LOCALAPPDATA%/AoE2Overlay\n\nPara atualizar o programa instalado:\n1. Aplique o atualizador aos arquivos do projeto.\n2. Execute gerar_atualizacao.py com Python 3.12.\n3. Informe uma versão superior à última gerada.\n4. Feche o aplicativo e execute o novo instalador.\n\nModificar os arquivos do projeto não modifica automaticamente o executável instalado.\n\nA interface móvel acompanha a versão servida pelo PC. Depois da atualização, reinicie e reconecte pelo novo QR Code.'), ('Atualização e desempenho', 'Com a atualização contínua aplicada, o próximo ciclo começa quando o anterior termina.\n\nA velocidade depende da leitura, da renderização e da rede. Não há garantia de uma taxa fixa.\n\nO jogo pode gravar os registros em blocos. Consultar mais rapidamente não disponibiliza informações que ainda não foram gravadas.\n\nO intervalo visível das ordens é apenas um filtro do histórico; não é o intervalo de atualização.'), ('Resolver problemas', 'Mapa vazio:\nAbra um replay válido, confirme a pasta e aguarde os dados iniciais ficarem disponíveis.\n\nInterface antiga:\nConfirme que o atualizador terminou sem erros. Gere e instale uma nova versão. Verifique se o atalho abre a cópia correta.\n\nOverlay invisível:\nConfira Exibir overlay, posição e opacidade. Use Testar por 10 segundos e confira o foco do jogo.\n\nÍcones ausentes:\nConfira Construções, Gaia e os filtros Ocultar. Verifique também as marcações manuais de recursos.\n\nCelular sem conexão:\nConfira a rede, mantenha o painel ligado e escaneie o QR Code atual. Experimente outro IP listado.\n\nErro ao iniciar:\nConsulte aplicativo.log e falha_inicializacao.log na pasta de dados, quando existirem.\n\nA geração das imagens usa Edge ou Chrome instalado no PC. Ícones ainda indisponíveis podem exigir internet no primeiro download.'), ('Limites das informações', 'O aplicativo lê o mapa inicial e os comandos gravados no replay. Ele não executa a simulação completa da partida.\n\nNão confirma posições atuais, construções concluídas, tecnologias concluídas, unidades vivas, mortes, conversões, destruições ou recursos restantes.\n\nContadores representam pedidos identificados. Ordens repetidas ou canceladas podem permanecer na contagem.\n\nAs rotas mostram destinos solicitados. As conexões de paliçadas são aproximações.\n\nOcultar manualmente um recurso é uma anotação do usuário, não uma detecção automática de coleta.\n\nA ausência de um ícone pode resultar dos filtros ativos ou da falta de identificação na fonte.')]

def normalizar(texto):
    return ''.join((caractere for caractere in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(caractere)))

def instalar(window, top, side):
    global TOPICS
    from idiomas_app import ajuda_localizada
    TOPICS = ajuda_localizada(TOPICS)
    if getattr(window, '_ajuda_instalada', False):
        return
    window._ajuda_instalada = True
    window._help_window = None

    def abrir(event=None):
        existente = window._help_window
        if existente is not None and existente.winfo_exists():
            existente.deiconify()
            existente.lift()
            existente.focus_set()
            return 'break'
        popup = tk.Toplevel(window.root)
        window._help_window = popup
        popup.title('Ajuda · Replay Companion')
        popup.configure(bg=BG)
        popup.transient(window.root)
        popup.geometry(f'{min(1020, popup.winfo_screenwidth() - 80)}x{min(760, popup.winfo_screenheight() - 120)}')
        popup.minsize(740, 480)
        header = tk.Frame(popup, bg=CARD)
        header.pack(fill='x')
        tk.Label(header, text='?  Central de ajuda', bg=CARD, fg=ACCENT, font=(window.title_font, 22, 'bold')).pack(side='left', padx=18, pady=16)
        tk.Label(header, text='F1 · Ajuda     Ctrl + F · Buscar', bg=CARD, fg=MUTED, font=(window.body_font, 10)).pack(side='right', padx=18)
        searchrow = tk.Frame(popup, bg=BG)
        searchrow.pack(fill='x', padx=16, pady=12)
        tk.Label(searchrow, text='Buscar na ajuda', bg=BG, fg=TEXT).pack(side='left', padx=(0, 10))
        query = tk.StringVar(master=popup)
        popup.help_query = query
        search = ttk.Entry(searchrow, textvariable=query)
        search.pack(side='left', fill='x', expand=True)
        ttk.Button(searchrow, text='Limpar', command=lambda: query.set('')).pack(side='left', padx=(8, 0))
        body = tk.Frame(popup, bg=BG)
        body.pack(fill='both', expand=True, padx=16, pady=(0, 12))
        left = tk.Frame(body, bg=CARD)
        left.pack(side='left', fill='y', padx=(0, 12))
        topics = tk.Listbox(left, width=28, bg=CARD, fg=TEXT, selectbackground=ACCENT, selectforeground='#201910', activestyle='none', exportselection=False, borderwidth=0, highlightthickness=1, highlightbackground=EDGE, font=(window.body_font, 11))
        bar = ttk.Scrollbar(left, command=topics.yview)
        bar.pack(side='right', fill='y')
        topics.configure(yscrollcommand=bar.set)
        topics.pack(fill='both', expand=True)
        right = tk.Frame(body, bg=CARD)
        right.pack(fill='both', expand=True)
        text = tk.Text(right, bg=CARD, fg=TEXT, wrap='word', padx=20, pady=16, borderwidth=0, font=(window.body_font, 11), spacing3=10, highlightthickness=1, highlightbackground=EDGE)
        scroll = ttk.Scrollbar(right, command=text.yview)
        scroll.pack(side='right', fill='y')
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill='both', expand=True)
        text.tag_configure('title', font=(window.title_font, 20, 'bold'), foreground=ACCENT, spacing3=18)
        footer = tk.Frame(popup, bg=BG)
        footer.pack(side='bottom', before=body, fill='x', padx=16, pady=(0, 12))
        count = tk.Label(footer, bg=BG, fg=MUTED)
        count.pack(side='left')
        ttk.Button(footer, text='Fechar ajuda', command=popup.destroy).pack(side='right')
        filtered = []

        def display(title, content):
            text.configure(state='normal')
            text.delete('1.0', 'end')
            text.insert('end', title + '\n\n', 'title')
            text.insert('end', content.strip())
            text.configure(state='disabled')
            text.yview_moveto(0)

        def select(event=None):
            indices = topics.curselection()
            if indices:
                display(*filtered[indices[0]])

        def rebuild(*args):
            wanted = normalizar(query.get().strip())
            filtered[:] = [item for item in TOPICS if wanted in normalizar(item[0] + ' ' + item[1])]
            topics.delete(0, 'end')
            for title, _ in filtered:
                topics.insert('end', title)
            count.configure(text=f'{len(filtered)} de {len(TOPICS)} tópicos')
            if filtered:
                topics.selection_set(0)
                topics.activate(0)
                display(*filtered[0])
            else:
                display('Nenhum tópico encontrado', 'Tente mapa, QR, unidades, configurações ou atualização. Use Limpar para voltar à lista completa.')

        def focus_search(event=None):
            search.focus_set()
            search.selection_range(0, 'end')
            return 'break'
        topics.bind('<<ListboxSelect>>', select)
        query.trace_add('write', rebuild)
        popup.bind('<Control-f>', focus_search)
        popup.bind('<Control-F>', focus_search)
        popup.bind('<Escape>', lambda event: popup.destroy())
        rebuild()
        search.focus_set()
        popup.help_topics = topics
        popup.help_text = text
        return 'break'
    window.abrir_ajuda = abrir
    button = ttk.Button(top, text='? Ajuda', style='Help.TButton', command=abrir, takefocus=True)
    children = top.winfo_children()
    button.pack(side='left', after=children[1], padx=12, pady=8)
    window.help_button = button
    window.monitor_label.configure(wraplength=160)
    window.root.bind('<F1>', abrir, add='+')
