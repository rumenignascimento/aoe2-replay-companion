import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r'''
import json
import os
from pathlib import Path
import tempfile
import tkinter as tk
from tkinter import ttk


def localizar_savegame():
    home = Path.home()
    bases = [
        home / "Games",
        home / "Saved Games",
        home / "Documents",
    ]

    for nome in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if os.environ.get(nome):
            base = Path(os.environ[nome])
            bases.extend([
                base / "Games",
                base / "Documents",
                base / "Saved Games",
            ])

    if os.name == "nt":
        try:
            import winreg
            chave = (
                r"Software\Microsoft\Windows\CurrentVersion"
                r"\Explorer\User Shell Folders"
            )
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, chave) as registro:
                for nome in (
                    "Personal",
                    "{4C5C32FF-BB9D-43B0-BF21-3E5395D0E7B3}",
                ):
                    try:
                        valor, _ = winreg.QueryValueEx(registro, nome)
                        bases.append(Path(os.path.expandvars(valor)))
                    except OSError:
                        pass
        except OSError:
            pass

    candidatos = {}
    for base in bases:
        jogo = base / "Age of Empires 2 DE"
        try:
            pastas = [jogo / "savegame", *jogo.glob("*/savegame")]
            for pasta in pastas:
                if not pasta.is_dir():
                    continue
                tempos = [
                    p.stat().st_mtime
                    for p in pasta.glob("*.aoe2record")
                    if p.is_file()
                ]
                candidatos[str(pasta)] = (
                    bool(tempos),
                    max(tempos, default=pasta.stat().st_mtime),
                )
        except OSError:
            continue

    if not candidatos:
        return None

    return Path(max(
        candidatos,
        key=lambda p: (candidatos[p], p),
    ))


def configurar_savegame(config):
    config = Path(config)
    try:
        dados = (
            json.loads(config.read_text(encoding="utf-8-sig"))
            if config.exists() else {}
        )
        if not isinstance(dados, dict):
            return None
        if dados.get("folder") and Path(dados["folder"]).is_dir():
            return Path(dados["folder"])
    except (OSError, ValueError):
        return None

    pasta = localizar_savegame()
    if pasta is None:
        return None

    dados["folder"] = str(pasta)
    config.parent.mkdir(parents=True, exist_ok=True)
    fd, temporario = tempfile.mkstemp(
        prefix="config-", suffix=".tmp", dir=config.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
        os.replace(temporario, config)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)
    return pasta


def pagina_rolavel(root):
    caixa = ttk.Frame(root)
    caixa.pack(fill="both", expand=True)
    caixa.rowconfigure(0, weight=1)
    caixa.columnconfigure(0, weight=1)

    canvas = tk.Canvas(caixa, highlightthickness=0, borderwidth=0)
    vertical = ttk.Scrollbar(
        caixa, orient="vertical", command=canvas.yview
    )
    horizontal = ttk.Scrollbar(
        caixa, orient="horizontal", command=canvas.xview
    )
    canvas.configure(
        yscrollcommand=vertical.set,
        xscrollcommand=horizontal.set,
    )

    canvas.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")

    pagina = ttk.Frame(canvas, padding=16)
    item = canvas.create_window(
        0, 0, window=pagina, anchor="nw"
    )
    pendente = [False]

    def ajustar():
        pendente[0] = False
        if not canvas.winfo_exists():
            return
        largura = max(
            canvas.winfo_width(), pagina.winfo_reqwidth()
        )
        altura = max(
            canvas.winfo_height(), pagina.winfo_reqheight()
        )
        canvas.itemconfigure(item, width=largura, height=altura)
        canvas.configure(scrollregion=(0, 0, largura, altura))

    def agendar(event=None):
        if not pendente[0]:
            pendente[0] = True
            canvas.after_idle(ajustar)

    def roda(event):
        widget = event.widget
        if widget.winfo_toplevel() != root:
            return
        if isinstance(
            widget,
            (tk.Text, tk.Listbox, ttk.Combobox,
             tk.Spinbox, ttk.Spinbox),
        ):
            return
        if not event.delta:
            return
        passos = max(1, abs(event.delta) // 120)
        if event.delta > 0:
            passos = -passos
        if event.state & 1:
            canvas.xview_scroll(passos, "units")
        else:
            canvas.yview_scroll(passos, "units")
        return "break"

    canvas.bind("<Configure>", agendar)
    pagina.bind("<Configure>", agendar)
    root.bind("<MouseWheel>", roda, add="+")
    return pagina
'''


class AdaptarGerador(ast.NodeTransformer):
    def __init__(self):
        self.lista = False
        self.launcher = False
        self.instalador = False

    def visit_List(self, node):
        self.generic_visit(node)
        valores = [
            item.value for item in node.elts
            if isinstance(item, ast.Constant)
            and isinstance(item.value, str)
        ]
        if (
            "painel_jogadores.py" in valores
            and "mapa_overlay.py" in valores
        ):
            if "interface_011.py" not in valores:
                node.elts.append(ast.Constant("interface_011.py"))
            self.lista = True
        return node

    def visit_Constant(self, node):
        if not isinstance(node.value, str):
            return node

        texto = node.value

        if "import painel_jogadores as painel" in texto:
            if "configurar_savegame" not in texto:
                padrao = r"(?m)^([ \t]*)import painel_jogadores as painel"
                resultado = re.search(padrao, texto)
                if not resultado:
                    raise RuntimeError(
                        "Não consegui adaptar a inicialização."
                    )
                espaco = resultado.group(1)
                linhas = [
                    "from interface_011 import configurar_savegame",
                    'configurar_savegame(DATA_DIR / "configuracoes_aoe2.json")',
                    'if "--configurar-savegame" in sys.argv:',
                    "    return",
                    "import painel_jogadores as painel",
                ]
                bloco = "\n".join(espaco + linha for linha in linhas)
                texto = re.sub(
                    padrao, lambda _: bloco, texto, count=1
                )
            self.launcher = True

        if "[Setup]" in texto and "[Run]" in texto:
            if "--configurar-savegame" not in texto:
                entrada = (
                    'Filename: "{app}\\AoE2Overlay.exe"; '
                    'Parameters: "--configurar-savegame"; '
                    'Flags: runhidden waituntilterminated\n'
                )
                texto = texto.replace(
                    "[Run]", "[Run]\n" + entrada, 1
                )
            self.instalador = True

        return ast.copy_location(ast.Constant(texto), node)


def main():
    pasta = Path(__file__).resolve().parent
    nomes = [
        "mapa_overlay.py",
        "painel_aoe2.py",
        "gerar_instalador.py",
    ]
    for nome in nomes:
        if not (pasta / nome).is_file():
            raise RuntimeError(
                f"Não encontrei {nome}. "
                "Execute na pasta completa do projeto."
            )

    alterados = {}

    mapa = (pasta / "mapa_overlay.py").read_text(
        encoding="utf-8-sig"
    )
    if "page=pagina_rolavel(root)" not in mapa:
        padrao = (
            r"page\s*=\s*ttk\.Frame\(root,\s*padding\s*=\s*16\)"
            r"\s*;\s*page\.pack\(fill\s*=\s*['\"]both['\"],"
            r"\s*expand\s*=\s*True\)"
        )
        mapa, quantidade = re.subn(
            padrao,
            "from interface_011 import pagina_rolavel; "
            "page=pagina_rolavel(root)",
            mapa,
            count=1,
        )
        if quantidade != 1:
            raise RuntimeError(
                "A estrutura de mapa_overlay.py mudou. "
                "Nenhum arquivo foi alterado."
            )
    alterados["mapa_overlay.py"] = mapa

    painel = (pasta / "painel_aoe2.py").read_text(
        encoding="utf-8-sig"
    )
    if "configurar_savegame(self.config_path)" not in painel:
        padrao = r"(?m)^([ \t]*)self\.load_settings\(\)[ \t]*$"
        resultado = re.search(padrao, painel)
        if not resultado:
            raise RuntimeError(
                "Não encontrei o carregamento das configurações. "
                "Nenhum arquivo foi alterado."
            )
        espaco = resultado.group(1)
        bloco = "\n".join([
            espaco + "from interface_011 import configurar_savegame",
            espaco + "configurar_savegame(self.config_path)",
            espaco + "self.load_settings()",
        ])
        painel = re.sub(
            padrao, lambda _: bloco, painel, count=1
        )
    alterados["painel_aoe2.py"] = painel

    gerador = (pasta / "gerar_instalador.py").read_text(
        encoding="utf-8-sig"
    )
    adaptador = AdaptarGerador()
    arvore = adaptador.visit(ast.parse(gerador))
    ast.fix_missing_locations(arvore)

    if not all((
        adaptador.lista,
        adaptador.launcher,
        adaptador.instalador,
    )):
        raise RuntimeError(
            "O gerador é diferente da versão esperada. "
            "Nenhum arquivo foi alterado."
        )

    alterados["gerar_instalador.py"] = ast.unparse(arvore) + "\n"
    alterados["interface_011.py"] = MODULO.lstrip()

    # Valida todos os arquivos antes de modificar o projeto.
    for nome, texto in alterados.items():
        ast.parse(texto, filename=nome)

    data = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = pasta / "backups_atualizacoes" / data
    backup.mkdir(parents=True)

    for nome in alterados:
        origem = pasta / nome
        if origem.exists():
            shutil.copy2(origem, backup / nome)

    for nome, texto in alterados.items():
        (pasta / nome).write_text(texto, encoding="utf-8")

    print("\nAlterações aplicadas.")
    print(f"Backup: {backup}")
    print("\nAgora execute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.1.1.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"\nERRO: {erro}")
        raise SystemExit(1)