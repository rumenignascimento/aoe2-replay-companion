import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r"""
import copy
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk


HOUSES = {70, 191, 192, 463, 464, 465}

MILITARY = {
    12, 45, 49, 72, 79, 82, 87, 101, 103, 104,
    117, 155, 209, 234, 235, 236, 487, 598,
    792, 1251, 1665, 1806,
}

ECONOMIC = {
    50, 68, 71, 84, 109, 141, 142, 276,
    562, 584, 621, 1021, 1734, 1754,
    1808, 1889, 2556,
}

KEYS = (
    "hide_military_buildings",
    "hide_economic_buildings",
    "hide_houses",
)


def category(ident, reference):
    if ident in HOUSES:
        return 2
    if ident in MILITARY:
        return 0
    if ident in ECONOMIC:
        return 1

    name = str(
        reference.get("objects", {}).get(str(ident), "")
    ).strip().casefold()

    if name.startswith("house"):
        return 2

    if any(
        word in name
        for word in (
            "barracks", "archery range", "stable",
            "siege workshop", "castle", "krepost",
            "donjon", "monastery", "church",
            "blacksmith", "university", "tower",
            "outpost", "wall", "gate", "dock",
        )
    ):
        return 0

    if any(
        word in name
        for word in (
            "town center", "mill", "market",
            "lumber camp", "mining camp", "farm",
            "folwark", "feitoria", "caravanserai",
            "mule cart", "pasture", "settlement", "wonder",
        )
    ):
        return 1

    return None


def ativar(g):
    if g.get("_filtros_construcoes_ativos"):
        return
    g["_filtros_construcoes_ativos"] = True

    g["p"].CONFIG_DEFAULTS.update({
        key: False for key in KEYS
    })

    flags = [False, False, False]
    original = g["app"].map_svg
    ns = g["NS"]

    def render(session):
        hidden = getattr(
            g["CONTEXT"],
            "building_filters",
            tuple(flags),
        )
        svg = original(session)

        if not any(hidden):
            return svg

        root = ET.fromstring(svg)

        for parent in list(root.iter()):
            for node in list(parent):
                ident = node.get("data-building-id")

                if ident is None:
                    continue

                try:
                    kind = category(
                        int(ident), session.reference
                    )
                except (ValueError, TypeError):
                    continue

                if kind is None or not hidden[kind]:
                    continue

                # Preserva a identificação da posição inicial
                # dos jogadores, mesmo ocultando o ícone do TC.
                if node.get("data-kind") == "initial":
                    for child in node:
                        if (
                            child.tag == "{" + ns + "}text"
                            and (child.text or "").startswith("J")
                        ):
                            parent.append(
                                copy.deepcopy(child)
                            )

                parent.remove(node)

        return ET.tostring(root, encoding="unicode")

    g["app"].map_svg = render
    g["mini"].minimap_svg = render
    g["selected_map"] = render

    Base = g["Window"]

    class Window(Base):
        def __init__(self, root, native):
            for key in KEYS:
                setattr(
                    self,
                    key,
                    tk.BooleanVar(master=root, value=False),
                )

            super().__init__(root, native)

            for key in KEYS:
                getattr(self, key).trace_add(
                    "write", self.building_filter_options
                )

            self.building_filter_options()

        def building_filter_options(self, *args):
            flags[:] = [
                bool(getattr(self, key).get())
                for key in KEYS
            ]
            self.next_frame = 0

        def job(self, *args, **kwargs):
            g["CONTEXT"].building_filters = tuple(flags)

            try:
                return super().job(*args, **kwargs)
            finally:
                del g["CONTEXT"].building_filters

        def navigate(self, name):
            super().navigate(name)

            if name != "Minimapa":
                return

            parent = self.advanced_body
            children = parent.winfo_children()

            box = ttk.LabelFrame(
                parent,
                text="Ocultar ícones de construções",
                padding=8,
            )
            box.pack(
                fill="x",
                pady=8,
                before=children[0] if children else None,
            )

            for label, key in zip(
                (
                    "Ocultar militares",
                    "Ocultar econômicas",
                    "Ocultar casas",
                ),
                KEYS,
            ):
                self.switch(
                    box, label, getattr(self, key)
                )

            ttk.Label(
                box,
                text=(
                    "Afeta apenas ícones. Contagens, rotas "
                    "e linhas de paliçadas permanecem.\n"
                    "O controle Construções continua sendo "
                    "o interruptor geral."
                ),
                wraplength=460,
            ).pack(anchor="w", pady=6)

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

            if "filtros_construcoes.py" not in nomes:
                node.elts.append(
                    ast.Constant("filtros_construcoes.py")
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
                + ". Execute na pasta completa do projeto."
            )

    alterados = {
        "filtros_construcoes.py": MODULO.lstrip()
    }

    codigo = (pasta / "painel_jogadores.py").read_text(
        encoding="utf-8-sig"
    )

    if "_ativar_filtros_construcoes(globals())" not in codigo:
        integracao = (
            "\n\nfrom filtros_construcoes import ativar "
            "as _ativar_filtros_construcoes\n"
            "_ativar_filtros_construcoes(globals())"
        )

        codigo, quantidade = re.subn(
            r"(?m)^_ativar_central_replay"
            r"\(globals\(\)\)[ \t]*$",
            lambda resultado: resultado.group() + integracao,
            codigo,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Integração da central não reconhecida. "
                "Nenhum arquivo foi alterado."
            )

    alterados["painel_jogadores.py"] = codigo

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
            arquivo_ajuda.read_text(
                encoding="utf-8-sig"
            )
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
                    topico[0] == "Ocultar construções por tipo"
                    for topico in topicos
                ):
                    topicos.append((
                        "Ocultar construções por tipo",
                        (
                            "Abra Minimapa e localize Ocultar ícones "
                            "de construções.\n\n"
                            "Ative separadamente Ocultar militares, "
                            "Ocultar econômicas e Ocultar casas.\n\n"
                            "Militares incluem produção de exército, "
                            "ferreiro, universidade, mosteiro e defesas. "
                            "Econômicas incluem centros urbanos, "
                            "mercados, moinhos e acampamentos de coleta. "
                            "As casas têm controle próprio.\n\n"
                            "Os filtros afetam a prévia, o overlay e "
                            "os mapas do celular no próximo quadro. "
                            "Não alteram os contadores de pedidos "
                            "nem as linhas de paliçadas.\n\n"
                            "As posições iniciais dos jogadores "
                            "continuam identificadas. Construções "
                            "é o interruptor geral da camada.\n\n"
                            "Salvar configurações mantém a seleção. "
                            "Tipos novos sem classificação permanecem "
                            "visíveis enquanto o interruptor geral "
                            "estiver ligado."
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

    print("\nFiltros de construções adicionados.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.7 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)