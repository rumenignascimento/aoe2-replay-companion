import ast
import shutil
from datetime import datetime
from pathlib import Path

MODULO = r'''
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from central_replay import CARD, TEXT, BRONZE


def mix(a, b, fraction):
    return tuple(round(x + (y - x) * fraction) for x, y in zip(a, b))


def aplicar_tema(window):
    style = ttk.Style(window.root)
    images = []
    window._finish_images = images

    def photo(image):
        result = ImageTk.PhotoImage(image, master=window.root)
        images.append(result)
        return result

    def button(top, bottom, border, highlight, pressed=False):
        image = Image.new("RGBA", (32, 32))
        draw = ImageDraw.Draw(image)
        offset = 1 if pressed else 0
        end = 30 if pressed else 29

        draw.rectangle((1, end + 1, 30, 31), fill="#0c0f0d")

        a = tuple(bytes.fromhex(top.lstrip("#")))
        b = tuple(bytes.fromhex(bottom.lstrip("#")))

        for y in range(offset, end + 1):
            color = mix(a, b, (y - offset) / max(1, end - offset))
            draw.line((0, y, 31, y), fill=color)

        draw.rectangle((0, offset, 31, end), outline=border, width=1)
        draw.line((1, offset, 30, offset), fill=highlight, width=1)
        return photo(image)

    palettes = {
        "Iron": (
            "#373d36", "#252b27", "#77664c", "#998467",
            "#424a40", "#30372f", "#2e342e", "#252b25",
        ),
        "Primary": (
            "#d9b171", "#b68a4c", "#826033", "#f5d79e",
            "#e6c28a", "#c89c5a", "#c49756", "#a77a3c",
        ),
        "Test": (
            "#80603b", "#594227", "#a48150", "#c7a36d",
            "#87643b", "#654b2b", "#70512f", "#543c23",
        ),
    }

    for name, colors in palettes.items():
        a, b, border, highlight, ha, hb, pa, pb = colors
        normal = button(a, b, border, highlight)
        hover = button(ha, hb, border, highlight)
        pressed = button(pa, pb, border, border, True)
        disabled = button(
            "#3b3e37", "#2e332e", "#514d3f", "#696759"
        )

        element = "Finish." + name + ".surface"

        if element not in style.element_names():
            style.element_create(
                element, "image", normal,
                ("disabled", disabled),
                ("pressed", pressed),
                ("active", hover),
                border=(3, 3, 3, 5),
                sticky="nsew",
            )

        names = {
            "Iron": ("TButton", "Help.TButton"),
            "Primary": ("Primary.TButton", "Accent.TButton"),
            "Test": ("Test.TButton",),
        }[name]

        for target in names:
            style.layout(target, [
                (element, {
                    "sticky": "nswe",
                    "children": [
                        ("Button.focus", {
                            "sticky": "nswe",
                            "children": [
                                ("Button.padding", {
                                    "sticky": "nswe",
                                    "children": [
                                        ("Button.label", {"sticky": "nswe"})
                                    ],
                                })
                            ],
                        })
                    ],
                })
            ])

            foreground = (
                "#21190f" if name == "Primary"
                else "#fff0d8" if name == "Test"
                else TEXT
            )

            style.configure(
                target,
                foreground=foreground,
                background=CARD,
                padding=(14, 12, 14, 14),
                borderwidth=0,
                focuscolor=(
                    "#4a311a" if name == "Primary" else "#e7c58b"
                ),
                font=(
                    window.body_font,
                    10,
                    "bold" if name in ("Primary", "Test") else "normal",
                ),
            )

            style.map(
                target,
                padding=[("pressed", (14, 13, 14, 13))],
                foreground=[("disabled", "#a5a398")],
            )

    def tab(selected=False, hover=False):
        image = Image.new("RGBA", (32, 24))
        draw = ImageDraw.Draw(image)
        y = 0 if selected else 3

        fill = (
            CARD if selected
            else "#20251f" if hover
            else "#171c19"
        )

        draw.rectangle((0, y, 31, 23), fill=fill)
        draw.line((0, y + 1, 0, 23), fill="#6c5c44")
        draw.line((31, y + 1, 31, 23), fill="#6c5c44")
        draw.line(
            (0, y, 31, y),
            fill="#d4ab68" if selected else "#544c3c",
        )
        draw.line(
            (0, 23, 31, 23),
            fill=CARD if selected else "#66573f",
        )
        return photo(image)

    inactive = tab()
    active = tab(True)
    hover = tab(False, True)
    element = "Finish.Notebook.tab"

    if element not in style.element_names():
        style.element_create(
            element, "image", inactive,
            ("selected", active),
            ("active", hover),
            border=(3, 4, 3, 1),
            sticky="nsew",
        )

    style.layout("TNotebook.Tab", [
        (element, {
            "sticky": "nswe",
            "children": [
                ("Notebook.padding", {
                    "side": "top",
                    "sticky": "nswe",
                    "children": [
                        ("Notebook.focus", {
                            "side": "top",
                            "sticky": "nswe",
                            "children": [
                                ("Notebook.label", {
                                    "side": "top",
                                    "sticky": "",
                                })
                            ],
                        })
                    ],
                })
            ],
        })
    ])

    style.configure(
        "TNotebook.Tab",
        padding=(14, 9),
        foreground=TEXT,
        background=CARD,
        focuscolor=BRONZE,
        font=(window.body_font, 10),
    )
    style.map(
        "TNotebook.Tab",
        expand=[("selected", (0, 0, 0, 1))],
    )

    image = Image.new("RGBA", (20, 20), CARD)
    ImageDraw.Draw(image).rectangle(
        (0, 0, 19, 19), outline="#6c5c44", width=1
    )
    client = photo(image)
    element = "Finish.Notebook.client"

    if element not in style.element_names():
        style.element_create(
            element, "image", client,
            border=1, sticky="nsew",
        )

    style.layout("TNotebook", [
        (element, {"sticky": "nswe"})
    ])
    style.configure(
        "TNotebook",
        background=CARD,
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )


def atualizar_navegacao(window):
    states = getattr(window, "_finish_nav", None)
    if states is None:
        return

    for name, button in window.nav_buttons.items():
        active = name == window.central_nav

        button.configure(
            bg="#2a302b" if active else "#1e2221",
            fg=TEXT,
            activebackground="#2a302b" if active else "#2b322b",
            activeforeground=TEXT,
            relief="sunken" if active else "flat",
            borderwidth=1 if active else 0,
            highlightthickness=0,
            padx=17 if active else 18,
            pady=13 if active else 14,
        )

        stripe = states[name]
        if active:
            stripe.place(x=0, y=0, width=3, relheight=1)
        else:
            stripe.place_forget()


def preparar_navegacao(window):
    if getattr(window, "_finish_nav", None) is not None:
        atualizar_navegacao(window)
        return

    window._finish_nav = {}

    for name, button in window.nav_buttons.items():
        stripe = tk.Frame(button, bg="#be914f", borderwidth=0)
        stripe.bind(
            "<Button-1>",
            lambda event, b=button: b.invoke(),
        )
        window._finish_nav[name] = stripe

        def enter(event, n=name, b=button):
            if window.central_nav != n:
                b.configure(bg="#2b322b")

        def leave(event, n=name, b=button):
            if window.central_nav != n:
                b.configure(bg="#1e2221")

        button.bind("<Enter>", enter, add="+")
        button.bind("<Leave>", leave, add="+")

    atualizar_navegacao(window)
'''


class Build(ast.NodeTransformer):
    def __init__(self):
        self.encontrou = False

    def visit_List(self, node):
        self.generic_visit(node)
        names = [
            v.value for v in node.elts
            if isinstance(v, ast.Constant)
            and isinstance(v.value, str)
        ]

        if "painel_jogadores.py" in names and "central_replay.py" in names:
            self.encontrou = True
            if "acabamento_visual.py" not in names:
                node.elts.append(ast.Constant("acabamento_visual.py"))

        return node


class Buttons(ast.NodeTransformer):
    def __init__(self):
        self.found = set()

    def visit_Call(self, node):
        self.generic_visit(node)

        if ast.unparse(node.func) != "ttk.Button":
            return node

        text = next((
            k.value.value
            for k in node.keywords
            if k.arg == "text"
            and isinstance(k.value, ast.Constant)
            and isinstance(k.value.value, str)
        ), None)

        target = (
            "Primary.TButton" if text == "Abrir replay"
            else "Test.TButton"
            if text and text.startswith("Testar por 10")
            else None
        )

        if target:
            self.found.add(target)
            existing = next((
                k for k in node.keywords if k.arg == "style"
            ), None)

            if existing:
                existing.value = ast.Constant(target)
            else:
                node.keywords.append(
                    ast.keyword(arg="style", value=ast.Constant(target))
                )

        return node


def main():
    root = Path(__file__).resolve().parent

    for name in (
        "central_replay.py",
        "ajuda_replay.py",
        "gerar_instalador.py",
    ):
        if not (root / name).is_file():
            raise RuntimeError(
                "Arquivo ausente: " + name
                + ". Execute na pasta completa do projeto."
            )

    changes = {"acabamento_visual.py": MODULO}

    tree = ast.parse(
        (root / "central_replay.py").read_text(encoding="utf-8-sig")
    )
    adapter = Buttons()
    tree = adapter.visit(tree)

    if adapter.found != {"Primary.TButton", "Test.TButton"}:
        raise RuntimeError(
            "Botões principais não reconhecidos. "
            "Nenhum arquivo foi alterado."
        )

    hooks = {
        "theme": "aplicar_tema",
        "build_central": "preparar_navegacao",
        "navigate": "atualizar_navegacao",
    }
    found = set()

    for cls in ast.walk(tree):
        if not isinstance(cls, ast.ClassDef) or cls.name != "Window":
            continue

        for method in cls.body:
            if not isinstance(method, ast.FunctionDef):
                continue
            if method.name not in hooks:
                continue

            name = hooks[method.name]
            found.add(method.name)

            already = any(
                isinstance(n, ast.Call)
                and ast.unparse(n.func) == name
                for n in ast.walk(method)
            )

            if not already:
                method.body.extend(ast.parse(
                    "from acabamento_visual import " + name
                    + "\n" + name + "(self)"
                ).body)

    if found != set(hooks):
        raise RuntimeError("Estrutura da central diferente do esperado.")

    ast.fix_missing_locations(tree)
    changes["central_replay.py"] = ast.unparse(tree) + "\n"

    tree = ast.parse(
        (root / "ajuda_replay.py").read_text(encoding="utf-8-sig")
    )
    found = False

    for method in tree.body:
        if not isinstance(method, ast.FunctionDef):
            continue
        if method.name != "instalar":
            continue

        start = next((
            i for i, n in enumerate(method.body)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "options"
                for t in n.targets
            )
        ), None)

        if start is None:
            start = next((
                i for i, n in enumerate(method.body)
                if isinstance(n, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "button"
                    for t in n.targets
                )
                and isinstance(n.value, ast.Call)
                and ast.unparse(n.value.func) == "ttk.Button"
            ), None)

        if start is None:
            raise RuntimeError(
                "Botão Ajuda não reconhecido. "
                "Nenhum arquivo foi alterado."
            )

        tail = """
button = ttk.Button(
    top, text="? Ajuda", style="Help.TButton",
    command=abrir, takefocus=True
)
children = top.winfo_children()
button.pack(side="left", after=children[1], padx=12, pady=8)
window.help_button = button
window.monitor_label.configure(wraplength=160)
window.root.bind("<F1>", abrir, add="+")
"""
        method.body = method.body[:start] + ast.parse(tail).body
        found = True

    if not found:
        raise RuntimeError("Integração da Ajuda não reconhecida.")

    ast.fix_missing_locations(tree)
    changes["ajuda_replay.py"] = ast.unparse(tree) + "\n"

    adapter = Build()
    tree = adapter.visit(ast.parse(
        (root / "gerar_instalador.py").read_text(encoding="utf-8-sig")
    ))

    if not adapter.encontrou:
        raise RuntimeError("Gerador diferente do esperado.")

    ast.fix_missing_locations(tree)
    changes["gerar_instalador.py"] = ast.unparse(tree) + "\n"

    for name, text in changes.items():
        ast.parse(text, filename=name)

    backup = (
        root / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for name in changes:
        if (root / name).exists():
            shutil.copy2(root / name, backup / name)

    for name, text in changes.items():
        (root / name).write_text(text, encoding="utf-8")

    print("Acabamento visual aplicado.")
    print("Backup:", backup)
    print("Agora execute: py -3.12 gerar_atualizacao.py")
    print("Versão sugerida: 0.3.0, ou superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("ERRO:", erro)
        raise SystemExit(1)