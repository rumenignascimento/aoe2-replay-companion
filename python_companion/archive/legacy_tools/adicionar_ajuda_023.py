import ast
from datetime import datetime
from pathlib import Path
import shutil


AJUDA = r"""
import tkinter as tk
from tkinter import ttk
import unicodedata
from central_replay import BG, CARD, EDGE, TEXT, MUTED

ACCENT = "#e0b56c"

TOPICS = [
    ("Comece aqui", '''
1. Clique em Abrir replay para analisar um arquivo .aoe2record.
2. Para acompanhar novas partidas, escolha Pasta savegame e selecione a pasta usada pelo jogo.
3. Escolha Todos ou um jogador no filtro acima do mapa.
4. Ajuste as camadas abaixo da prévia e os controles do overlay à direita.
5. Use Salvar configurações para manter os ajustes ao reabrir o aplicativo.

A prévia funciona com o aplicativo em foco, mesmo que o overlay esteja desligado.
'''),

    ("Replay e monitoramento", '''
Abrir replay: escolha um arquivo .aoe2record existente, inclusive de uma partida já iniciada.

Pasta savegame / Alterar pasta: inicia o monitoramento dos novos arquivos dessa pasta. Arquivos que já estavam nela não são abertos automaticamente; use Abrir replay.

A pasta pode ser localizada automaticamente nos locais usuais do jogo. Confirme o perfil correto se houver várias contas. É possível alterá-la manualmente.

O leitor só recebe informações que o jogo já gravou no arquivo. Se o jogo estiver mantendo dados em memória, as novas ordens poderão demorar a aparecer.
'''),

    ("Visão geral e jogadores", '''
A área central mostra o mapa inicial, os pedidos identificáveis e os destinos solicitados das tropas.

O filtro Todos reúne os jogadores; Jogador 1, Jogador 2 etc. filtra os dados daquele participante. As cores seguem o replay.

Os três resumos abaixo do mapa contam pedidos de construção, comandos de produção militar e solicitações de pesquisa. Não são quantidades vivas.

A seleção no celular é independente: mudar um filtro no celular não altera o filtro do PC.
'''),

    ("Overlay do mapa", '''
Exibir overlay liga ou desliga o minimapa sobre o jogo.

Largura altera seu tamanho; Opacidade ajusta sua transparência. Na aba Posição, escolha um canto e informe as margens X e Y em pixels.

Testar por 10 segundos permite conferir o posicionamento mesmo fora do jogo. Esse teste também ativa Exibir overlay.

Ctrl + Alt + M alterna a visibilidade. Durante o uso normal, o overlay acompanha o foco da janela do Age of Empires II DE.

Se ele não aparecer, confira a caixa Exibir overlay e teste o jogo em modo janela sem bordas.
'''),

    ("Minimapa e camadas", '''
Terreno: mostra ou oculta as cores do terreno.

Deslocamentos: mostra ou oculta as ordens de movimentação.

Construções: mostra ou oculta construções, centros urbanos e traçados de paredes no mapa; não apaga os dados registrados.

Pesquisas e eras: controla a apresentação das solicitações de pesquisa na barra.

Em Minimapa ficam os ajustes avançados: rotação, espelhamento, tamanho dos ícones de construções e tropas e intervalo visível das ordens.

O intervalo visível das ordens é a janela de histórico mostrada no mapa. Ele não controla a velocidade de atualização.
'''),

    ("Rotas e deslocamentos", '''
Linhas tracejadas representam destinos solicitados. Os pontos numerados indicam a sequência identificada das ordens com Shift.

O leitor trata os comandos de movimento pelo terreno e pelo minimapa no formato validado com os replays do projeto. Uma ordem normal substitui a sequência anterior; uma ordem enfileirada acrescenta destinos.

Os ícones identificam tipos conhecidos e o número indica as unidades identificadas no grupo. O tipo de unidades novas pode continuar desconhecido.

R indica uma referência de origem: posição inicial ou destino pedido anteriormente. Não comprova a posição atual, a saída ou a chegada da tropa.
'''),

    ("Barra militar e pesquisas", '''
Abra Overlay para ajustar a barra de pedidos: visibilidade, posição, margens, tamanho dos ícones e opacidade.

Produção militar na barra controla os pedidos de produção. Os contadores não descontam mortes ou conversões, porque a fonte atual não fornece um estado vivo confiável.

Os ícones menores ao lado das construções representam solicitações de tecnologias. Avanços de era também podem aparecer quando identificáveis.

Uma tecnologia solicitada não significa que foi concluída. A associação com uma construção pode vir do alvo inicial ou dos metadados do jogo.
'''),

    ("Paliçadas e recursos", '''
Madeira, ouro, pedra, alimentos, relíquias e objetos iniciais vêm do mapa inicial do replay. O mapa não confirma os recursos restantes após coleta.

Paliçadas iniciais aparecem como linhas sólidas; os trechos solicitados aparecem tracejados.

Bolinhas indicam extremidades sem conexão identificável. São possíveis aberturas, não falhas comprovadas. A ausência de bolinhas também não garante que um muro esteja fechado ou concluído.

A opção de marcar possíveis aberturas fica na seção Minimapa.
'''),

    ("Ordens e relatórios", '''
A seção Ordens mostra os registros e resumos disponíveis para o jogador selecionado.

Abrir relatórios abre a pasta dos arquivos gerados para a partida. A fonte pode incluir mapa, imagens e registros em JSON ou texto.

Os horários mostrados se referem ao tempo de jogo registrado no replay.

Se uma contagem não estiver disponível, isso não significa que o jogador tenha zero unidades ou construções. Pedidos cancelados ou repetidos podem permanecer na contagem de comandos.
'''),

    ("Atalhos", '''
Atalhos abre a configuração das teclas para selecionar jogadores.

Padrões:
• Ctrl + Alt + 0 mostra Todos.
• Ctrl + Alt + 1 a 8 seleciona o jogador.
• Ctrl + Alt + seta direita ou esquerda alterna a seleção.

Use Aplicar atalhos para testar e Salvar configurações para persistir. Um campo vazio desativa aquele atalho. Combinações ocupadas por outro programa podem ser recusadas.

Ctrl + Alt + M é reservado para o overlay.

F1 abre esta ajuda com a janela do aplicativo em foco. Dentro da ajuda, Ctrl + F foca a busca.
'''),

    ("Celular e QR Code", '''
No PC, abra Celular / tablet · QR Code ou use o menu Celular / tablet. Clique em Iniciar / atualizar QR.

Conecte o celular à mesma rede local do PC. O PC pode estar conectado por cabo ao mesmo roteador. Escaneie o QR Code e abra o endereço no navegador.

Se houver vários endereços, escolha o correspondente à rede do celular. Se o Windows solicitar, permita acesso em redes privadas.

Mantenha o programa aberto no PC. Desligar painel encerra o acesso. Depois de reiniciar o programa, escaneie o novo QR Code.

O painel é uma segunda tela: não envia comandos ao jogo.
'''),

    ("Gestos e tela cheia", '''
No celular, use a pinça: abra dois dedos sobre o mapa para ampliar e aproxime-os para reduzir.

Arraste um dedo para deslocar o mapa ampliado. O controle Zoom continua disponível.

Minimapa em tela cheia amplia o painel, mantendo o filtro de jogadores e o zoom. Toque em Sair da tela cheia para voltar.

Quando o navegador não permitir tela cheia nativa, o painel ocupa a área disponível da página. Girar o aparelho pode ampliar a área útil.

Fora da área do mapa, os gestos normais de rolagem da página continuam disponíveis.
'''),

    ("Salvar e restaurar", '''
Salvar configurações mantém os ajustes de mapa, camadas, overlay, barra e atalhos para a próxima abertura.

Restaurar configurações originais volta aos padrões e salva esses padrões. Os ajustes personalizados anteriores serão substituídos.

Na versão instalada, configurações, cache de ícones, relatórios e logs ficam em %LOCALAPPDATA%/AoE2Overlay.

A atualização pelo instalador preserva essa pasta. Alterações nos arquivos do projeto só chegam ao programa instalado depois de gerar e instalar uma nova versão.
'''),

    ("Atualizações e desempenho", '''
No projeto, execute gerar_atualizacao.py com Python 3.12 e informe uma versão superior à última gerada. Feche o aplicativo e execute o novo instalador.

A interface móvel acompanha a compilação do PC. Depois de atualizar e reiniciar, reconecte pelo novo QR Code para carregar a página atualizada.

Com a atualização contínua aplicada, o próximo ciclo começa quando o anterior termina. A velocidade depende da leitura, da renderização e da rede; não há garantia de uma taxa fixa.

O jogo pode gravar os registros em blocos. Consultar mais rápido não produz dados que ainda não foram gravados.
'''),

    ("Resolver problemas", '''
Mapa vazio: abra um replay válido ou confirme a pasta monitorada. Aguarde o cabeçalho do arquivo ficar disponível.

Interface antiga: confirme que o atualizador terminou sem erros, gere o instalador e abra o executável mais recente. O atalho pode apontar para outra cópia.

Celular sem conexão: confira a rede, mantenha o painel ligado, escolha outro IP listado e escaneie o QR Code atual.

Overlay invisível: ative sua visibilidade, use o teste por 10 segundos e confira a posição, opacidade e foco do jogo.

Erro ao iniciar: consulte aplicativo.log e falha_inicializacao.log na pasta de dados, quando esses arquivos existirem.

A geração das imagens usa Edge ou Chrome instalado no PC. Ícones ainda não disponíveis podem exigir internet para o primeiro download.
'''),

    ("Limites das informações", '''
O programa lê o estado inicial e comandos do arquivo de replay. Ele não executa a simulação completa do jogo.

Não confirma posições atuais, construções concluídas, conclusão de tecnologias, unidades vivas, mortes, conversões ou recursos restantes.

Os contadores representam pedidos ou comandos identificados. Os tipos conhecidos de unidades vêm dos objetos iniciais; novas instâncias podem não ter tipo identificável.

As rotas e conexões de paliçadas são referências derivadas dos registros. Use essas informações com as limitações indicadas na interface.
'''),
]


def normalizar(texto):
    return "".join(
        caractere
        for caractere in unicodedata.normalize(
            "NFKD", texto.casefold()
        )
        if not unicodedata.combining(caractere)
    )


def instalar(window, top, side):
    if getattr(window, "_ajuda_instalada", False):
        return
    window._ajuda_instalada = True
    window._help_window = None

    def abrir(event=None):
        existente = window._help_window

        if existente is not None and existente.winfo_exists():
            existente.deiconify()
            existente.lift()
            existente.focus_set()
            return "break"

        popup = tk.Toplevel(window.root)
        window._help_window = popup
        popup.title("Ajuda · Replay Companion")
        popup.configure(bg=BG)
        popup.transient(window.root)
        popup.geometry(
            f"{min(1020, popup.winfo_screenwidth()-80)}"
            f"x{min(760, popup.winfo_screenheight()-120)}"
        )
        popup.minsize(740, 480)

        header = tk.Frame(popup, bg=CARD)
        header.pack(fill="x")

        tk.Label(
            header,
            text="?  Central de ajuda",
            bg=CARD,
            fg=ACCENT,
            font=(window.title_font, 22, "bold"),
        ).pack(side="left", padx=18, pady=16)

        tk.Label(
            header,
            text="F1 · Ajuda     Ctrl + F · Buscar",
            bg=CARD,
            fg=MUTED,
            font=(window.body_font, 10),
        ).pack(side="right", padx=18)

        searchrow = tk.Frame(popup, bg=BG)
        searchrow.pack(fill="x", padx=16, pady=12)

        tk.Label(
            searchrow,
            text="Buscar na ajuda",
            bg=BG,
            fg=TEXT,
        ).pack(side="left", padx=(0, 10))

        query = tk.StringVar(master=popup)
        popup.help_query = query

        search = ttk.Entry(
            searchrow, textvariable=query
        )
        search.pack(
            side="left", fill="x", expand=True
        )

        ttk.Button(
            searchrow,
            text="Limpar",
            command=lambda: query.set(""),
        ).pack(side="left", padx=(8, 0))

        body = tk.Frame(popup, bg=BG)
        body.pack(
            fill="both", expand=True,
            padx=16, pady=(0, 12),
        )

        left = tk.Frame(body, bg=CARD)
        left.pack(
            side="left", fill="y", padx=(0, 12)
        )

        topics = tk.Listbox(
            left,
            width=28,
            bg=CARD,
            fg=TEXT,
            selectbackground=ACCENT,
            selectforeground="#201910",
            activestyle="none",
            exportselection=False,
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=EDGE,
            font=(window.body_font, 11),
        )

        bar = ttk.Scrollbar(
            left, command=topics.yview
        )
        bar.pack(side="right", fill="y")
        topics.configure(yscrollcommand=bar.set)
        topics.pack(fill="both", expand=True)

        right = tk.Frame(body, bg=CARD)
        right.pack(fill="both", expand=True)

        text = tk.Text(
            right,
            bg=CARD,
            fg=TEXT,
            wrap="word",
            padx=20,
            pady=16,
            borderwidth=0,
            font=(window.body_font, 11),
            spacing3=10,
            highlightthickness=1,
            highlightbackground=EDGE,
        )

        scroll = ttk.Scrollbar(
            right, command=text.yview
        )
        scroll.pack(side="right", fill="y")
        text.configure(yscrollcommand=scroll.set)
        text.pack(fill="both", expand=True)

        text.tag_configure(
            "title",
            font=(window.title_font, 20, "bold"),
            foreground=ACCENT,
            spacing3=18,
        )

        footer = tk.Frame(popup, bg=BG)
        footer.pack(
            side="bottom", before=body,
            fill="x", padx=16, pady=(0, 12),
        )

        count = tk.Label(
            footer, bg=BG, fg=MUTED
        )
        count.pack(side="left")

        ttk.Button(
            footer,
            text="Fechar ajuda",
            command=popup.destroy,
        ).pack(side="right")

        filtered = []

        def display(title, content):
            text.configure(state="normal")
            text.delete("1.0", "end")
            text.insert(
                "end", title + "\n\n", "title"
            )
            text.insert("end", content.strip())
            text.configure(state="disabled")
            text.yview_moveto(0)

        def select(event=None):
            indices = topics.curselection()
            if indices:
                display(*filtered[indices[0]])

        def rebuild(*args):
            wanted = normalizar(
                query.get().strip()
            )
            filtered[:] = [
                item for item in TOPICS
                if wanted in normalizar(
                    item[0] + " " + item[1]
                )
            ]

            topics.delete(0, "end")
            for title, _ in filtered:
                topics.insert("end", title)

            count.configure(
                text=(
                    f"{len(filtered)} de "
                    f"{len(TOPICS)} tópicos"
                )
            )

            if filtered:
                topics.selection_set(0)
                topics.activate(0)
                display(*filtered[0])
            else:
                display(
                    "Nenhum tópico encontrado",
                    "Tente mapa, QR, unidades, configurações "
                    "ou atualização. Use Limpar para voltar "
                    "à lista completa.",
                )

        def focus_search(event=None):
            search.focus_set()
            search.selection_range(0, "end")
            return "break"

        topics.bind(
            "<<ListboxSelect>>", select
        )
        query.trace_add("write", rebuild)

        popup.bind("<Control-f>", focus_search)
        popup.bind("<Control-F>", focus_search)
        popup.bind(
            "<Escape>",
            lambda event: popup.destroy(),
        )

        rebuild()
        search.focus_set()

        popup.help_topics = topics
        popup.help_text = text
        return "break"

    window.abrir_ajuda = abrir

    options = dict(
        text="?  AJUDA",
        command=abrir,
        bg=ACCENT,
        fg="#201910",
        activebackground="#f2cc89",
        activeforeground="#201910",
        font=(window.body_font, 10, "bold"),
        padx=12,
        pady=14,
        borderwidth=0,
        highlightthickness=2,
        highlightbackground=ACCENT,
        highlightcolor=TEXT,
        takefocus=True,
    )

    button = tk.Button(top, **options)
    children = top.winfo_children()
    button.pack(
        side="left",
        after=children[1],
        padx=12,
        pady=8,
    )
    window.help_button = button

    tk.Button(side, **options).pack(
        side="bottom",
        fill="x",
        padx=12,
        pady=(10, 6),
    )

    window.monitor_label.configure(
        wraplength=160
    )
    window.root.bind("<F1>", abrir, add="+")
"""


class Build(ast.NodeTransformer):
    def __init__(self):
        self.encontrou = False

    def visit_List(self, node):
        self.generic_visit(node)

        nomes = [
            item.value for item in node.elts
            if isinstance(item, ast.Constant)
            and isinstance(item.value, str)
        ]

        if (
            "painel_jogadores.py" in nomes
            and "central_replay.py" in nomes
        ):
            self.encontrou = True

            if "ajuda_replay.py" not in nomes:
                node.elts.append(
                    ast.Constant("ajuda_replay.py")
                )

        return node


def main():
    pasta = Path(__file__).resolve().parent

    for nome in (
        "central_replay.py",
        "gerar_instalador.py",
    ):
        if not (pasta / nome).is_file():
            raise RuntimeError(
                "Arquivo ausente: " + nome
                + ". Aplique primeiro a atualização "
                "da central de replay."
            )

    arvore = ast.parse(
        (pasta / "central_replay.py").read_text(
            encoding="utf-8-sig"
        )
    )
    quantidade = 0

    for classe in ast.walk(arvore):
        if (
            isinstance(classe, ast.ClassDef)
            and classe.name == "Window"
        ):
            for metodo in classe.body:
                if (
                    isinstance(metodo, ast.FunctionDef)
                    and metodo.name == "build_central"
                ):
                    quantidade += 1

                    existe = any(
                        isinstance(item, ast.ImportFrom)
                        and item.module == "ajuda_replay"
                        for item in ast.walk(metodo)
                    )

                    if not existe:
                        metodo.body.extend(ast.parse(
                            "from ajuda_replay import instalar "
                            "as instalar_ajuda\n"
                            "instalar_ajuda(self, top, side)"
                        ).body)

    if quantidade != 1:
        raise RuntimeError(
            "Estrutura da central diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)

    adaptador = Build()
    gerador = adaptador.visit(ast.parse(
        (pasta / "gerar_instalador.py").read_text(
            encoding="utf-8-sig"
        )
    ))

    if not adaptador.encontrou:
        raise RuntimeError(
            "O gerador não contém a central de replay. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(gerador)

    alterados = {
        "central_replay.py": ast.unparse(arvore) + "\n",
        "gerar_instalador.py": ast.unparse(gerador) + "\n",
        "ajuda_replay.py": AJUDA.lstrip(),
    }

    for nome, texto in alterados.items():
        ast.parse(texto, filename=nome)

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for nome in alterados:
        origem = pasta / nome
        if origem.exists():
            shutil.copy2(origem, backup / nome)

    for nome, texto in alterados.items():
        (pasta / nome).write_text(
            texto, encoding="utf-8"
        )

    print("\nAjuda adicionada ao topo, menu lateral e F1.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.3 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)