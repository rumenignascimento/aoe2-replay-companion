"""Remove interrogações da barra e oculta ícones desconhecidos."""
import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile
import textwrap


HELPERS = r'''
# BARRA_SEM_INTERROGACOES_V1

def _known_bar_icon(kind, ident):
    if kind not in ("building", "unit", "tech") or ident is None:
        return None

    path = RESEARCH.paths.get((kind, ident))

    if path is None and kind == "building":
        path = (
            t.ROOT / "icones_aoe2"
            / f"building_{ident}.png"
        )

    if path is None and kind == "unit":
        path = (
            t.ROOT / "icones_aoe2"
            / f"troop_{ident}.png"
        )

    return (
        path if path is not None and path.is_file()
        else None
    )


def research_rows(state, show_units=True, show_research=True):
    result = []

    for kind, ident, count, techs in _bar_rows_original(
        state, show_units, show_research
    ):
        if _known_bar_icon(kind, ident) is None:
            continue

        known_techs = tuple(
            (tech, requests)
            for tech, requests in techs
            if _known_bar_icon("tech", tech) is not None
        )
        result.append((
            kind, ident, count, known_techs
        ))

    return result


_report_before_clean_bar = p.state_report


def _report_clean_bar(state):
    return (
        "CONTADORES DA BARRA = PEDIDOS REGISTRADOS, "
        "NÃO QUANTIDADES VIVAS.\n"
        "O leitor atual não confirma produção, mortes, "
        "conversões ou destruição efetiva.\n\n"
        + _report_before_clean_bar(state).replace(
            "Número? =", "Número ="
        )
    )


p.state_report = _report_clean_bar

'''


PICTURE = '''
def picture(self, kind, ident, x, y, size):
    if not hasattr(self, "_research_photos"):
        self._research_photos = {}
        self._research_size = None

    if self._research_size != self._draw_size:
        self._research_photos.clear()
        self._research_size = self._draw_size

    key = kind, ident, int(size)

    if key not in self._research_photos:
        path = _known_bar_icon(kind, ident)
        if path is None:
            return False

        try:
            photo = tk.PhotoImage(
                master=self.root, file=str(path)
            )
            ratio = Fraction(
                max(1, int(size)),
                max(photo.width(), photo.height()),
            )
            self._research_photos[key] = (
                photo.zoom(ratio.numerator)
                .subsample(ratio.denominator)
            )
        except (OSError, tk.TclError):
            self._research_photos[key] = None

    photo = self._research_photos[key]

    if photo:
        self.canvas.create_image(
            x + size / 2, y + size / 2,
            image=photo,
        )
        return True

    return False
'''


DRAW = '''
def draw_research_bar(self, rows, size):
    self._draw_size = size
    self.canvas.delete("all")

    pad = max(3, round(size * .12))
    row = round(size * 1.25)
    header = max(12, round(size * .30)) + pad
    maxtech = max(
        (len(item[3]) for item in rows), default=0
    )
    width = math.ceil(
        pad * 2 + size * 2.4 + maxtech * size * .65
    )

    self.canvas.create_text(
        pad, pad,
        text="PEDIDOS",
        fill="white",
        anchor="nw",
        font=(
            "Segoe UI",
            max(8, round(size * .20)),
            "bold",
        ),
    )

    visible = 0

    for kind, ident, count, techs in rows:
        y = pad + header + visible * row

        if not self.picture(kind, ident, pad, y, size):
            continue

        if count is not None:
            self.canvas.create_text(
                pad + size * 1.6,
                y + size * .5,
                text=str(count),
                fill="white",
                font=(
                    "Segoe UI",
                    max(9, round(size * .45)),
                    "bold",
                ),
            )

        slot = 0

        for tech, requests in techs:
            xx = pad + size * 2.4 + slot * size * .65
            yy = y + size * .25

            if self.picture(
                "tech", tech, xx, yy, size // 2
            ):
                if requests > 1:
                    self.canvas.create_text(
                        xx + size * .5,
                        yy + size * .5,
                        text=str(requests),
                        fill="white",
                        anchor="se",
                        font=(
                            "Segoe UI",
                            max(6, round(size * .16)),
                            "bold",
                        ),
                    )
                slot += 1

        visible += 1

    height = max(
        1, pad * 2 + header + row * visible
    )
    self.canvas.configure(
        width=width, height=height
    )
    self.caption_size = width, height
'''


NOTICE = '''
def setup_clean_bar_notice(self):
    self.root.title(
        "AoE2 — barra de pedidos registrados"
    )

    def update_labels(parent):
        for widget in parent.winfo_children():
            if isinstance(widget, ttk.Label):
                text = str(widget.cget("text"))
                if "Número? =" in text:
                    widget.configure(
                        text=text.replace(
                            "Número? =", "Número ="
                        )
                    )

            if isinstance(
                widget, (ttk.Frame, ttk.LabelFrame)
            ):
                update_labels(widget)

    update_labels(self.report.master)
'''


class ReserveHeader(ast.NodeTransformer):
    def visit_Constant(self, node):
        if (
            isinstance(node.value, float)
            and node.value == 0.3
        ):
            node.value = 0.7
        return node


def install():
    folder = Path(__file__).resolve().parent
    target = folder / "painel_melhorado.py"

    if not target.is_file():
        raise RuntimeError(
            "Coloque o atualizador na pasta "
            "de painel_melhorado.py."
        )

    source = target.read_text(encoding="utf-8-sig")

    if "# BARRA_SEM_INTERROGACOES_V1" in source:
        print("A limpeza da barra já está instalada.")
        return

    tree = ast.parse(source)
    window = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "Window"
    )
    methods = {
        node.name: node
        for node in window.body
        if isinstance(node, ast.FunctionDef)
    }
    rows = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "research_rows"
    )

    edits = []
    start, end = rows.lineno - 1, rows.end_lineno
    rows.name = "_bar_rows_original"
    edits.append((
        start, end, ast.unparse(rows) + "\n"
    ))

    for name, code in (
        ("picture", PICTURE),
        ("draw_research_bar", DRAW),
    ):
        node = methods[name]
        edits.append((
            node.lineno - 1,
            node.end_lineno,
            textwrap.indent(
                textwrap.dedent(code).strip(), "    "
            ) + "\n",
        ))

    node = ast.fix_missing_locations(
        ReserveHeader().visit(methods["tick"])
    )
    edits.append((
        node.lineno - 1,
        node.end_lineno,
        textwrap.indent(
            ast.unparse(node), "    "
        ) + "\n",
    ))

    edits.extend([
        (
            window.lineno - 1,
            window.lineno - 1,
            HELPERS,
        ),
        (
            window.end_lineno,
            window.end_lineno,
            "\n" + textwrap.indent(
                NOTICE.strip(), "    "
            ) + "\n",
        ),
        (
            methods["__init__"].end_lineno,
            methods["__init__"].end_lineno,
            "\n        self.setup_clean_bar_notice()\n",
        ),
    ])

    lines = source.splitlines(keepends=True)
    for start, end, content in sorted(edits, reverse=True):
        lines[start:end] = [content]

    updated = "".join(lines)
    compile(updated, str(target), "exec")

    backup = target.with_name(
        "painel_melhorado.antes_limpeza_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".py"
    )
    shutil.copy2(target, backup)

    fd, name = tempfile.mkstemp(
        prefix=".barra-",
        suffix=".tmp",
        dir=folder,
    )
    try:
        with os.fdopen(
            fd, "w", encoding="utf-8"
        ) as handle:
            handle.write(updated)
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)

    print("Interrogações removidas da barra.")
    print("Backup:", backup.name)
    print(
        "Contagens continuam sendo pedidos, "
        "não sobreviventes."
    )


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print("Não foi possível atualizar:", exc)
        raise SystemExit(1)