import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r"""
import math
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


ECON_BUILDINGS = {
    68, 84, 109, 562, 584, 621,
    1021, 1734, 1754, 1808,
}
ECON_TECHS = {
    22, 54, 65, 213, 249,
    487, 499, 506, 629, 754,
}
MIL_TECHS = {8, 280}
SHARED_TECHS = {101, 102, 103}
ECON_NAMES = {
    "burgundian vineyards", "paper money", "silk road",
    "grand trunk road", "sultans", "nomads",
    "gillnets", "treadmill crane",
}
TABS = ("Economia", "Militar")


def technology_category(ident, record, producer):
    if ident in SHARED_TECHS:
        return "Ambas"
    if ident in MIL_TECHS:
        return "Militar"

    name = str(record.get("name", "")).strip().casefold()

    if ident in ECON_TECHS or name in ECON_NAMES:
        return "Economia"
    if producer in ECON_BUILDINGS:
        return "Economia"
    if producer is None:
        return "Ambas"

    return "Militar"


def divide_rows(rows, records, tab):
    result = []

    for owner, color, kind, ident, count, techs in rows:
        base = (
            "Economia"
            if kind == "building" and ident in ECON_BUILDINGS
            else "Militar"
        )

        selected = tuple(
            (tech, amount)
            for tech, amount in techs
            if technology_category(
                tech, records.get((owner, tech), {}), ident
            ) in (tab, "Ambas")
        )

        if base == tab or selected:
            result.append((
                owner, color, kind, ident,
                count if base == tab else None,
                selected,
            ))

    return result


def tile_base(row, size):
    digits = (
        len(str(row[4]))
        if row[4] is not None else 0
    )
    return math.ceil(max(
        size * 1.8 + 8,
        size + 12 + digits * max(10, int(size * .35)) * .75,
    ))


def panel_layout(rows, width, size, max_height):
    pad = 8
    header = 48
    owner_height = 18
    line = size + 14
    gap = 12
    step = size * .65
    expanded = []

    for row in rows:
        techs = row[5]
        capacity = int(
            (width - 2*pad - tile_base(row, size)) / step
        )

        if techs and capacity < 1:
            expanded.append(row[:5] + ((),))
            row = row[:4] + (None, techs)
            capacity = int(
                (width - 2*pad - tile_base(row, size)) / step
            )

        capacity = max(1, capacity)

        for start in range(
            0, max(1, len(techs)), capacity
        ):
            expanded.append(
                row[:4]
                + (
                    row[4] if start == 0 else None,
                    techs[start:start+capacity],
                )
            )

    pages = []
    items = []
    x = pad
    y = header
    owner = None

    def finish():
        nonlocal items, x, y, owner

        height = max(
            header + 40,
            math.ceil(y + (line if x > pad else 0) + pad),
        )
        pages.append(dict(
            items=items,
            height=min(max_height, height),
        ))
        items = []
        x = pad
        y = header
        owner = None

    for row in expanded:
        tile = tile_base(row, size) + len(row[5]) * step

        if owner != row[0]:
            if x > pad:
                y += line
                x = pad

            if (
                y + owner_height + line + pad > max_height
                and items
            ):
                finish()

            owner = row[0]
            items.append((
                "owner", owner, row[1], pad, y
            ))
            y += owner_height

        if x + tile > width - pad and x > pad:
            x = pad
            y += line

        if y + line + pad > max_height and items:
            finish()
            owner = row[0]
            items.append((
                "owner", owner, row[1], pad, y
            ))
            y += owner_height

        items.append(("item", row, x, y))
        x += tile + gap

    finish()
    return pages


def ativar(g):
    if g.get("_painel_horizontal_ativo"):
        return
    g["_painel_horizontal_ativo"] = True

    actions = [
        (
            "panel_economy", "Painel: Economia",
            -10, "Ctrl+Alt+E",
        ),
        (
            "panel_military", "Painel: Militar",
            -11, "Ctrl+Alt+R",
        ),
        (
            "panel_previous", "Painel: página anterior",
            -12, "Ctrl+Alt+PgUp",
        ),
        (
            "panel_next", "Painel: próxima página",
            -13, "Ctrl+Alt+PgDn",
        ),
    ]

    for key, label, target, chord in actions:
        g["ACTIONS"].append((key, label, target))
        g["DEFAULT_KEYS"][key] = chord
        g["p"].CONFIG_DEFAULTS["key_" + key] = chord

    g["p"].CONFIG_DEFAULTS.update(
        panel_tab="Economia",
        panel_width=900,
    )

    old_validate = g["p"]._validate_config

    def validate(values):
        if isinstance(values, dict):
            values = dict(values)
            used = set()

            for key in g["DEFAULT_KEYS"]:
                if "key_" + key in values:
                    chord = g["parse_key"](
                        values["key_" + key]
                    )
                    if chord is not None:
                        used.add(chord)

            # Preserva atalhos anteriores. Um novo padrão
            # conflitante começa desativado.
            for key, _, _, default in actions:
                if "key_" + key not in values:
                    chord = g["parse_key"](default)
                    values["key_" + key] = (
                        "" if chord in used else default
                    )
                    if chord not in used:
                        used.add(chord)

        result = old_validate(values)

        if result["panel_tab"] not in TABS:
            raise ValueError("Aba do painel inválida.")

        width = result["panel_width"]
        if (
            isinstance(width, bool)
            or not isinstance(width, int)
            or not 300 <= width <= 3600
        ):
            raise ValueError(
                "Largura do painel: use um inteiro "
                "entre 300 e 3600."
            )

        return result

    g["p"]._validate_config = validate
    Base = g["Window"]

    class Window(Base):
        def __init__(self, root, native):
            self.panel_tab = tk.StringVar(
                master=root, value="Economia"
            )
            self.panel_width = tk.IntVar(
                master=root, value=900
            )
            self.panel_page = 0
            self._panel_images = {}
            self._panel_notebook = None

            super().__init__(root, native)

            self.panel_tab.trace_add(
                "write", self.panel_changed
            )
            self.panel_width.trace_add(
                "write", self.panel_changed
            )

        def panel_changed(self, *args):
            self.panel_page = 0
            self.bar_cache = None
            notebook = self._panel_notebook

            if notebook is not None and notebook.winfo_exists():
                index = TABS.index(self.panel_tab.get())
                if notebook.index(notebook.select()) != index:
                    notebook.select(index)

        def choose(self, target):
            if target in (-10, -11):
                self.panel_tab.set(
                    TABS[0 if target == -10 else 1]
                )
                return

            if target in (-12, -13):
                self.panel_page += (
                    -1 if target == -12 else 1
                )
                self.bar_cache = None
                return

            return super().choose(target)

        def rows(self):
            records = {
                (player["player"], record["id"]): record
                for player in self.bar_state.get(
                    "per_player", []
                )
                for record in player.get(
                    "research_orders", []
                )
            }

            return divide_rows(
                Base.rows(self),
                records,
                self.panel_tab.get(),
            )

        def panel_photo(self, kind, ident, size):
            key = kind, ident, size

            if key not in self._panel_images:
                try:
                    with Image.open(
                        self.icon_path(kind, ident)
                    ) as original:
                        image = original.convert("RGBA")
                        image.thumbnail(
                            (size, size),
                            Image.Resampling.LANCZOS,
                        )

                        if max(image.size) < size:
                            ratio = size / max(image.size)
                            image = image.resize(
                                (
                                    round(image.width * ratio),
                                    round(image.height * ratio),
                                ),
                                Image.Resampling.LANCZOS,
                            )

                        self._panel_images[key] = (
                            ImageTk.PhotoImage(
                                image, master=self.root
                            )
                        )

                except (OSError, TypeError, tk.TclError):
                    self._panel_images[key] = None

            return self._panel_images[key]

        def paint_horizontal(
            self, page, width, size, index, total
        ):
            canvas = self.canvas
            canvas.delete("all")
            pad = 8
            body = getattr(
                self, "body_font", "Segoe UI"
            )

            for i, tab in enumerate(TABS):
                x = pad + i * 120
                active = self.panel_tab.get() == tab

                canvas.create_text(
                    x, 7,
                    text=tab,
                    anchor="nw",
                    fill="#e0b56c" if active else "#ddd5c6",
                    font=(body, 11, "bold"),
                )

                if active:
                    canvas.create_line(
                        x, 29, x+100, 29,
                        fill="#d5a05c", width=2,
                    )

            canvas.create_text(
                pad, 34,
                text=f"PEDIDOS · página {index+1}/{total}",
                anchor="nw",
                fill="#e8dfcf",
                font=(body, 8),
            )

            if not page["items"]:
                canvas.create_text(
                    pad, 59,
                    text="Sem pedidos identificáveis nesta aba.",
                    anchor="nw",
                    fill="white",
                    font=(body, 10),
                )

            for entry in page["items"]:
                if entry[0] == "owner":
                    _, owner, color, x, y = entry
                    canvas.create_text(
                        x, y,
                        text=f"J{owner}",
                        anchor="nw",
                        fill=color,
                        font=(body, 9, "bold"),
                    )
                    continue

                _, row, x, y = entry
                owner, color, kind, ident, count, techs = row

                image = self.panel_photo(
                    kind, ident, size
                )
                if image:
                    canvas.create_image(
                        x+size/2, y+size/2,
                        image=image,
                    )

                if count is not None:
                    canvas.create_text(
                        x+size+4, y+size/2,
                        text=str(count),
                        anchor="w",
                        fill="white",
                        font=(
                            body,
                            max(10, int(size*.35)),
                            "bold",
                        ),
                    )

                for i, (tech, amount) in enumerate(techs):
                    xx = (
                        x + tile_base(row, size)
                        + i * size * .65
                    )
                    image = self.panel_photo(
                        "tech", tech, size // 2
                    )

                    if image:
                        canvas.create_image(
                            xx+size/4, y+size/2,
                            image=image,
                        )

                    if amount > 1:
                        canvas.create_text(
                            xx+size*.5, y+size*.8,
                            text=str(amount),
                            anchor="se",
                            fill="white",
                            font=(body, 8, "bold"),
                        )

            canvas.configure(
                width=width, height=page["height"]
            )
            self.caption_size = width, page["height"]

        def update_horizontal_panel(self):
            game = self.native.game()

            if not (
                self.photo
                and self.caption_show.get()
                and (
                    game
                    or g["time"].monotonic()
                    < self.preview_until
                )
            ):
                self.caption.withdraw()
                return

            x, y, w, h = game or (
                0, 0,
                self.root.winfo_screenwidth(),
                self.root.winfo_screenheight(),
            )

            def number(var, default, low, high):
                try:
                    return min(
                        high, max(low, int(var.get()))
                    )
                except (ValueError, tk.TclError):
                    return default

            width = min(
                number(self.panel_width, 900, 300, 3600),
                max(160, w-16),
            )
            size = min(
                number(self.bar_size, 48, 24, 120),
                max(12, int((width-16)/2.5)),
            )
            size -= size % 2

            max_height = min(
                max(120, h-16),
                max(130, min(300, int(h*.4))),
            )
            size = min(
                size, max(12, max_height-90)
            )
            size -= size % 2

            rows = self.rows()

            while (
                size > 12
                and any(
                    tile_base(row, size) > width-16
                    for row in rows
                )
            ):
                size -= 2

            pages = panel_layout(
                rows, width, size, max_height
            )
            index = self.panel_page % len(pages)
            self.panel_page = index

            cache = (
                tuple(rows), size, width,
                max_height, index,
                self.panel_tab.get(),
                g["SELECTION"][0],
            )

            if cache != self.bar_cache:
                self.paint_horizontal(
                    pages[index], width, size,
                    index, len(pages),
                )
                self.bar_cache = cache

            self.caption.attributes(
                "-alpha", float(self.bar_opacity.get())
            )

            iw, ih = self.caption_size
            mx = number(self.caption_x, 20, 0, 10000)
            my = number(self.caption_y, 80, 0, 10000)
            corner = self.caption_corner.get()

            dx = (
                w-iw-mx
                if corner in (
                    "Superior direito", "Inferior direito"
                )
                else mx
            )
            dy = (
                h-ih-my
                if corner in (
                    "Inferior esquerdo", "Inferior direito"
                )
                else my
            )

            self.caption.geometry(f"{iw}x{ih}")
            self.caption.update_idletasks()

            self.native.u.SetWindowPos(
                self.caption_hwnd,
                None,
                x + max(0, min(max(0, w-iw), dx)),
                y + max(0, min(max(0, h-ih), dy)),
                iw, ih, 0x14,
            )
            self.caption.deiconify()

        def setup_horizontal_controls(self, name):
            if name != "Overlay":
                return

            parent = self.advanced_body
            children = parent.winfo_children()

            box = ttk.LabelFrame(
                parent,
                text="Painel horizontal",
                padding=8,
            )
            box.pack(
                fill="x",
                pady=8,
                before=children[0] if children else None,
            )

            notebook = ttk.Notebook(box)
            notebook.pack(fill="x")
            self._panel_notebook = notebook

            for tab in TABS:
                page = ttk.Frame(
                    notebook, padding=8
                )
                notebook.add(page, text=tab)

                ttk.Label(
                    page,
                    text=(
                        "Construções e pesquisas econômicas."
                        if tab == "Economia" else
                        "Produção, construções e pesquisas militares."
                    ),
                ).pack(anchor="w")

            notebook.select(
                TABS.index(self.panel_tab.get())
            )

            def select(event=None):
                tab = TABS[
                    notebook.index(notebook.select())
                ]
                if self.panel_tab.get() != tab:
                    self.panel_tab.set(tab)

            notebook.bind(
                "<<NotebookTabChanged>>", select
            )

            self.field(
                box,
                "Largura do painel (px)",
                self.panel_width,
                bounds=(300, 3600),
            )

            ttk.Label(
                box,
                text=(
                    "Avanços de era aparecem nas duas abas.\n"
                    "Atalhos e páginas podem ser ajustados em Atalhos."
                ),
                wraplength=450,
            ).pack(anchor="w", pady=6)

            ttk.Button(
                box,
                text="Página anterior",
                command=lambda: self.choose(-12),
            ).pack(side="left")

            ttk.Button(
                box,
                text="Próxima página",
                command=lambda: self.choose(-13),
            ).pack(side="left", padx=6)

        def keys_dialog(self):
            dialog = tk.Toplevel(self.root)
            dialog.title("Atalhos · jogadores e painel")
            dialog.geometry("620x650")

            footer = ttk.Frame(
                dialog, padding=10
            )
            footer.pack(side="bottom", fill="x")

            ttk.Button(
                footer,
                text="Aplicar atalhos",
                command=self.apply_keys,
            ).pack(side="left")

            ttk.Button(
                footer,
                text="Salvar configurações",
                command=self.save_settings,
            ).pack(side="left", padx=10)

            ttk.Label(
                dialog,
                text=(
                    "Campo vazio desativa o atalho. "
                    "Ctrl+Alt+M é reservado ao minimapa."
                ),
                wraplength=570,
            ).pack(fill="x", padx=12, pady=10)

            canvas = tk.Canvas(
                dialog,
                highlightthickness=0,
                bg=self.root.cget("bg"),
            )
            bar = ttk.Scrollbar(
                dialog, command=canvas.yview
            )
            bar.pack(side="right", fill="y")
            canvas.configure(
                yscrollcommand=bar.set
            )
            canvas.pack(fill="both", expand=True)

            body = ttk.Frame(
                canvas, padding=12
            )
            item = canvas.create_window(
                0, 0, window=body, anchor="nw"
            )

            body.bind(
                "<Configure>",
                lambda event: canvas.configure(
                    scrollregion=canvas.bbox("all")
                ),
            )
            canvas.bind(
                "<Configure>",
                lambda event: canvas.itemconfigure(
                    item, width=event.width
                ),
            )

            for row, (key, label, target) in enumerate(
                g["ACTIONS"]
            ):
                ttk.Label(
                    body, text=label
                ).grid(
                    row=row, column=0,
                    padx=8, pady=7, sticky="w",
                )

                ttk.Entry(
                    body,
                    textvariable=getattr(
                        self, "key_" + key
                    ),
                    width=26,
                ).grid(
                    row=row, column=1,
                    padx=8, pady=7,
                )

    g["Window"] = Window
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

            if "painel_horizontal.py" not in nomes:
                node.elts.append(
                    ast.Constant("painel_horizontal.py")
                )

        return node


class Labels(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        self.generic_visit(node)

        if node.name == "navigate":
            existe = any(
                isinstance(item, ast.Call)
                and ast.unparse(item.func)
                == "self.setup_horizontal_controls"
                for item in ast.walk(node)
            )

            if not existe:
                node.body.append(ast.parse(
                    "self.setup_horizontal_controls(name)"
                ).body[0])

        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            texto = node.value

            substituicoes = {
                "Exibir barra de pedidos":
                    "Exibir painel de pedidos",
                "Produção militar na barra":
                    "Produção militar no painel",
                "Posição da barra":
                    "Posição do painel",
                "Margem X da barra":
                    "Margem X do painel",
                "Margem Y da barra":
                    "Margem Y do painel",
                "Tamanho dos ícones da barra":
                    "Tamanho dos ícones do painel",
                "Opacidade da barra":
                    "Opacidade do painel",
            }

            for antigo, novo in substituicoes.items():
                texto = texto.replace(antigo, novo)

            return ast.copy_location(
                ast.Constant(texto), node
            )

        return node


def main():
    pasta = Path(__file__).resolve().parent

    for nome in (
        "painel_jogadores.py",
        "central_replay.py",
        "gerar_instalador.py",
    ):
        if not (pasta / nome).is_file():
            raise RuntimeError(
                "Arquivo ausente: " + nome
                + ". Execute na pasta completa "
                "da central de replay."
            )

    alterados = {
        "painel_horizontal.py": MODULO.lstrip()
    }

    texto = (pasta / "painel_jogadores.py").read_text(
        encoding="utf-8-sig"
    )

    if "_ativar_painel_horizontal(globals())" not in texto:
        integracao = (
            "from painel_horizontal import ativar "
            "as _ativar_painel_horizontal\n"
            "_ativar_painel_horizontal(globals())\n\n"
        )

        texto, quantidade = re.subn(
            r"(?m)^from central_replay import ativar.*$",
            lambda resultado: integracao + resultado.group(),
            texto,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Integração da central não reconhecida."
            )

    arvore = ast.parse(texto)
    quantidade = 0

    for classe in ast.walk(arvore):
        if (
            isinstance(classe, ast.ClassDef)
            and classe.name == "Window"
        ):
            for metodo in classe.body:
                if (
                    isinstance(metodo, ast.FunctionDef)
                    and metodo.name == "tick"
                ):
                    for indice, item in enumerate(metodo.body):
                        if (
                            isinstance(item, ast.Expr)
                            and isinstance(item.value, ast.Call)
                            and ast.unparse(item.value.func)
                            == "app.base.Window.tick"
                        ):
                            metodo.body = (
                                metodo.body[:indice+1]
                                + ast.parse(
                                    "if not self.closing:\n"
                                    "    self.update_horizontal_panel()"
                                ).body
                            )
                            quantidade += 1
                            break

    if quantidade != 1:
        raise RuntimeError(
            "Atualização do painel não reconhecida. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)
    alterados["painel_jogadores.py"] = (
        ast.unparse(arvore) + "\n"
    )

    arvore = Labels().visit(ast.parse(
        (pasta / "central_replay.py").read_text(
            encoding="utf-8-sig"
        )
    ))
    ast.fix_missing_locations(arvore)
    alterados["central_replay.py"] = (
        ast.unparse(arvore) + "\n"
    )

    adaptador = Build()
    arvore = adaptador.visit(ast.parse(
        (pasta / "gerar_instalador.py").read_text(
            encoding="utf-8-sig"
        )
    ))

    if not adaptador.encontrou:
        raise RuntimeError(
            "Gerador diferente do esperado."
        )

    ast.fix_missing_locations(arvore)
    alterados["gerar_instalador.py"] = (
        ast.unparse(arvore) + "\n"
    )

    arquivo_ajuda = pasta / "ajuda_replay.py"

    if arquivo_ajuda.exists():
        arvore = ast.parse(
            arquivo_ajuda.read_text(encoding="utf-8-sig")
        )

        for item in arvore.body:
            if (
                isinstance(item, ast.Assign)
                and any(
                    isinstance(alvo, ast.Name)
                    and alvo.id == "TOPICS"
                    for alvo in item.targets
                )
                and isinstance(item.value, ast.List)
            ):
                topicos = ast.literal_eval(item.value)

                if not any(
                    topico[0] == "Painel horizontal e abas"
                    for topico in topicos
                ):
                    topicos.append((
                        "Painel horizontal e abas",
                        (
                            "O painel substitui a barra vertical "
                            "e apresenta pedidos em duas abas: "
                            "Economia e Militar.\n\n"
                            "Construções e produção permanecem "
                            "nas categorias correspondentes. "
                            "Tecnologias são separadas pela função "
                            "conhecida e construção de origem. "
                            "Avanços de era aparecem nas duas abas.\n\n"
                            "Contagens de construções ficam na "
                            "categoria principal, sem duplicação. "
                            "Tecnologias com origem não identificada "
                            "podem aparecer nas duas abas.\n\n"
                            "Padrões: Ctrl+Alt+E para Economia; "
                            "Ctrl+Alt+R para Militar; "
                            "Ctrl+Alt+PgUp e PgDn para páginas. "
                            "Configure em Atalhos. Se um padrão "
                            "conflitar com uma configuração anterior, "
                            "a nova tecla poderá ficar desativada "
                            "até ser ajustada.\n\n"
                            "Em Overlay, ajuste largura, tamanho "
                            "dos ícones, posição e opacidade. "
                            "A seleção também pode ser feita "
                            "nas abas do aplicativo.\n\n"
                            "As abas desenhadas sobre o jogo "
                            "são indicativas: o overlay continua "
                            "sem capturar cliques. Para muitos itens, "
                            "use as páginas.\n\n"
                            "Os valores continuam sendo pedidos, "
                            "sem confirmar execução ou conclusão."
                        ),
                    ))

                item.value = ast.parse(
                    repr(topicos), mode="eval"
                ).body

        ast.fix_missing_locations(arvore)
        alterados["ajuda_replay.py"] = (
            ast.unparse(arvore) + "\n"
        )

    for nome, codigo in alterados.items():
        ast.parse(codigo, filename=nome)

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for nome in alterados:
        origem = pasta / nome
        if origem.exists():
            shutil.copy2(origem, backup / nome)

    for nome, codigo in alterados.items():
        (pasta / nome).write_text(
            codigo, encoding="utf-8"
        )

    print("\nPainel horizontal preparado.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.6 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)