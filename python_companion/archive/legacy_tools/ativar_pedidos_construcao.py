"""Ativa a contagem de pedidos de construção do jogador 2."""
import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile
import textwrap


SUPPORT = r'''
# BARRA_PEDIDOS_CONSTRUCAO_V1
from collections import Counter


class OrderSession(app.base.Session):
    def __init__(self, path):
        super().__init__(path)
        self.requested_building_counts = Counter()

    def apply(self, action, payload):
        super().apply(action, payload)

        if action != "BUILD":
            return

        player = payload.get("player_id")
        ids = payload.get("object_ids", [])

        if player is None and ids and ids[0] in self.objects:
            player = self.objects[ids[0]]["owner"]

        ident = payload.get("building_id")

        if player == 2 and ident in BUILDING_CATALOG:
            self.requested_building_counts[ident] += 1


def order_state(session):
    return {
        "player": 2,
        "game_ms": session.ms,
        "building_counts": dict(
            session.requested_building_counts
        ),
        "source": "replay_construction_orders",
        "meaning": (
            "Pedidos registrados; conclusão e existência "
            "atual não confirmadas."
        ),
    }


def state_report(state):
    entries = building_entries(state)
    lines = [
        "JOGADOR 2 — PEDIDOS DE CONSTRUÇÃO",
        f"Pedidos lidos até {app.base.game_time(state['game_ms'])}",
        "Número? = pedidos registrados; conclusão não confirmada.",
        "Pedidos repetidos ou posteriormente cancelados "
        "continuam na contagem.",
        "Não é a quantidade de edifícios existentes ou concluídos.",
        "Construções iniciais não entram: esta barra conta "
        "apenas pedidos.",
        "",
    ]

    if entries:
        lines.extend(
            f"{BUILDING_CATALOG[ident][0]}: {count} pedido(s)"
            for ident, count in entries
        )
    else:
        lines.append(
            "Nenhum pedido elegível do jogador 2 "
            "encontrado no trecho lido."
        )

    return "\n".join(lines)

'''


SETUP = '''
def setup_building_bar(self):
    self.root.title(
        "AoE2 — pedidos de construção do jogador 2"
    )

    for panel in self.report.master.winfo_children():
        if isinstance(panel, ttk.Label):
            if "Dados confirmados" in str(panel.cget("text")):
                panel.configure(
                    text="Pedidos de construção do jogador 2"
                )

        elif isinstance(panel, ttk.LabelFrame):
            if str(panel.cget("text")).startswith("Barra vertical"):
                panel.configure(
                    text="Barra vertical — pedidos do jogador 2"
                )

                for label in panel.winfo_children():
                    if isinstance(label, ttk.Label):
                        value = str(label.cget("text"))

                        if (
                            "ampulheta" in value
                            or "Um ícone por construção" in value
                        ):
                            label.configure(
                                text=(
                                    "Número? = pedidos registrados; "
                                    "conclusão não confirmada."
                                )
                            )
'''


class ChangeJob(ast.NodeTransformer):
    def visit_Call(self, node):
        node = self.generic_visit(node)

        if ast.unparse(node.func) == "app.base.Session":
            node.func = ast.Name(
                id="OrderSession",
                ctx=ast.Load(),
            )

        elif (
            isinstance(node.func, ast.Name)
            and node.func.id == "confirmed_state"
        ):
            node.func.id = "order_state"

        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            node.value = node.value.replace(
                "barra_confirmada.json",
                "pedidos_construcoes.json",
            )
        return node


class MarkOrders(ast.NodeTransformer):
    def visit_Call(self, node):
        node = self.generic_visit(node)

        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "str"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "count"
        ):
            return ast.JoinedStr(values=[
                ast.FormattedValue(
                    value=ast.Name(
                        id="count",
                        ctx=ast.Load(),
                    ),
                    conversion=-1,
                ),
                ast.Constant(value="?"),
            ])

        return node


def install():
    folder = Path(__file__).resolve().parent
    target = folder / "painel_aoe2.py"

    if not target.is_file():
        raise RuntimeError(
            "Coloque o atualizador na mesma pasta "
            "de painel_aoe2.py."
        )

    source = target.read_text(encoding="utf-8-sig")

    if "# BARRA_PEDIDOS_CONSTRUCAO_V1" in source:
        print("A contagem de pedidos já está instalada.")
        return

    tree = ast.parse(source)

    window = next(
        (
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "Window"
        ),
        None,
    )

    if (
        window is None
        or "BUILDING_CATALOG" not in source
        or "draw_building_icon" not in source
    ):
        raise RuntimeError(
            "É necessária a versão da barra com "
            "um ícone por tipo de construção."
        )

    methods = {
        node.name: node
        for node in window.body
        if isinstance(node, ast.FunctionDef)
    }

    required = {
        "job", "draw_bar", "setup_building_bar"
    }
    if not required <= methods.keys():
        raise RuntimeError(
            "Versão do painel não reconhecida. "
            "Nenhum arquivo foi alterado."
        )

    edits = []

    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in (
                "confirmed_state", "state_report"
            )
        ):
            edits.append((
                node.lineno - 1,
                node.end_lineno,
                "",
            ))

    for name, transformer in (
        ("job", ChangeJob()),
        ("draw_bar", MarkOrders()),
    ):
        node = ast.fix_missing_locations(
            transformer.visit(methods[name])
        )

        replacement = (
            textwrap.indent(
                ast.unparse(node), "    "
            )
            + "\n"
        )

        edits.append((
            node.lineno - 1,
            node.end_lineno,
            replacement,
        ))

    node = methods["setup_building_bar"]
    edits.append((
        node.lineno - 1,
        node.end_lineno,
        textwrap.indent(SETUP.strip(), "    ") + "\n",
    ))

    edits.append((
        window.lineno - 1,
        window.lineno - 1,
        SUPPORT,
    ))

    lines = source.splitlines(keepends=True)

    for start, end, content in sorted(
        edits, reverse=True
    ):
        lines[start:end] = [content]

    updated = "".join(lines)
    compile(updated, str(target), "exec")

    if (
        "OrderSession(path)" not in updated
        or "order_state(session)" not in updated
    ):
        raise RuntimeError(
            "Não foi possível atualizar a leitura "
            "de pedidos. Nada foi alterado."
        )

    backup = target.with_name(
        "painel_aoe2.antes_pedidos_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".py"
    )
    shutil.copy2(target, backup)

    fd, name = tempfile.mkstemp(
        prefix=".painel-",
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

    print("Atualização concluída. Backup:", backup.name)
    print(
        "A barra agora mostra pedidos, identificados com ?."
    )
    print("Abra painel_aoe2.py normalmente.")


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print("Não foi possível atualizar:", exc)
        raise SystemExit(1)