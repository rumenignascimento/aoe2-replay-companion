import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r"""
import tkinter as tk
from tkinter import ttk


LAYERS = (
    ("terrain", "Terreno", "map_terrain"),
    ("movements", "Deslocamentos", "troops_map"),
    ("buildings", "Construções", "central_buildings"),
    ("research", "Pesquisas e eras", "research_icons"),
    ("gaia", "Gaia", "gaia_show"),
    (
        "hide_military",
        "Ocultar militares",
        "hide_military_buildings",
    ),
    (
        "hide_economic",
        "Ocultar econômicas",
        "hide_economic_buildings",
    ),
    ("hide_houses", "Ocultar casas", "hide_houses"),
)


def ativar(g):
    if g.get("_controles_camadas_ativos"):
        return
    g["_controles_camadas_ativos"] = True

    additions = []

    for index, (key, label, variable) in enumerate(LAYERS):
        action = "layer_" + key
        target = -30 - index
        chord = f"Ctrl+Alt+Shift+{index+1}"

        g["ACTIONS"].append((
            action, "Camadas: " + label, target
        ))
        g["DEFAULT_KEYS"][action] = chord
        g["p"].CONFIG_DEFAULTS["key_" + action] = chord
        additions.append((action, chord))

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

            # Mantém combinações anteriormente salvas.
            for key, default in additions:
                if "key_" + key not in values:
                    chord = g["parse_key"](default)
                    values["key_" + key] = (
                        "" if chord in used else default
                    )
                    if chord not in used:
                        used.add(chord)

        return old_validate(values)

    g["p"]._validate_config = validate
    Base = g["Window"]

    class Window(Base):
        def __init__(self, root, native):
            self._position_slider_vars = {}
            self._position_slider_guards = set()
            super().__init__(root, native)

        def choose(self, target):
            index = -target - 30

            if 0 <= index < len(LAYERS):
                _, label, name = LAYERS[index]
                variable = getattr(self, name, None)

                if variable is None:
                    self.status.set(
                        "Camada indisponível nesta versão: "
                        + label
                    )
                    return

                variable.set(not bool(variable.get()))
                self.next_frame = 0
                return

            return super().choose(target)

        def add_position_slider(self, parent, axis):
            variable = getattr(
                self, "position_" + axis
            )

            limit = max(
                1,
                self.root.winfo_screenwidth()
                if axis == "x"
                else self.root.winfo_screenheight(),
            )

            try:
                value = float(variable.get())
            except (ValueError, tk.TclError):
                value = 0

            slider_value = tk.DoubleVar(
                master=self.root,
                value=max(0, min(limit, value)),
            )
            self._position_slider_vars[axis] = slider_value

            def from_slider(value):
                if axis in self._position_slider_guards:
                    return

                self._position_slider_guards.add(axis)

                try:
                    result = max(
                        0, min(10000, round(float(value)))
                    )
                    variable.set(str(result))
                    slider_value.set(min(limit, result))
                finally:
                    self._position_slider_guards.discard(axis)

            def from_field(*args):
                if axis in self._position_slider_guards:
                    return

                try:
                    value = float(variable.get())
                except (ValueError, tk.TclError):
                    return

                self._position_slider_guards.add(axis)

                try:
                    slider_value.set(
                        max(0, min(limit, value))
                    )
                finally:
                    self._position_slider_guards.discard(axis)

            variable.trace_add("write", from_field)

            slider = ttk.Scale(
                parent,
                from_=0,
                to=limit,
                variable=slider_value,
                command=from_slider,
            )
            slider.pack(
                fill="x", pady=(0, 10)
            )

            setattr(
                self, "position_slider_" + axis, slider
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

            if "controles_camadas.py" not in nomes:
                node.elts.append(
                    ast.Constant("controles_camadas.py")
                )

        return node


class Sliders(ast.NodeTransformer):
    def __init__(self, existentes):
        self.existentes = existentes
        self.eixos = set()

    def visit_Expr(self, node):
        self.generic_visit(node)
        chamada = node.value

        if (
            isinstance(chamada, ast.Call)
            and ast.unparse(chamada.func) == "self.field"
            and len(chamada.args) >= 3
            and ast.unparse(chamada.args[0]) == "position"
        ):
            for eixo in ("x", "y"):
                if (
                    ast.unparse(chamada.args[2])
                    == "self.position_" + eixo
                ):
                    self.eixos.add(eixo)

                    if eixo not in self.existentes:
                        extra = ast.parse(
                            "self.add_position_slider("
                            "position, " + repr(eixo) + ")"
                        ).body[0]
                        return [node, extra]

        return node


class HelpLabels(ast.NodeTransformer):
    def visit_Constant(self, node):
        if (
            isinstance(node.value, str)
            and re.fullmatch(r"\?\s*AJUDA", node.value)
        ):
            return ast.copy_location(
                ast.Constant("AJUDA"), node
            )

        return node


def main():
    pasta = Path(__file__).resolve().parent

    for nome in (
        "painel_jogadores.py",
        "central_replay.py",
        "painel_horizontal.py",
        "gerar_instalador.py",
        "ajuda_replay.py",
    ):
        if not (pasta / nome).is_file():
            raise RuntimeError(
                "Arquivo ausente: " + nome
                + ". Execute na pasta completa "
                "do projeto atualizado."
            )

    alterados = {
        "controles_camadas.py": MODULO.lstrip()
    }

    codigo = (pasta / "painel_jogadores.py").read_text(
        encoding="utf-8-sig"
    )

    if "_ativar_controles_029(globals())" not in codigo:
        integracao = (
            "from controles_camadas import ativar "
            "as _ativar_controles_029\n"
            "_ativar_controles_029(globals())\n\n"
        )

        codigo, quantidade = re.subn(
            r"(?m)^from painel_movel import ativar.*$",
            lambda resultado: integracao + resultado.group(),
            codigo,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Integração móvel não reconhecida. "
                "Nenhum arquivo foi alterado."
            )

    alterados["painel_jogadores.py"] = codigo

    arvore = ast.parse(
        (pasta / "central_replay.py").read_text(
            encoding="utf-8-sig"
        )
    )

    existentes = set()

    for item in ast.walk(arvore):
        if (
            isinstance(item, ast.Call)
            and ast.unparse(item.func)
            == "self.add_position_slider"
            and len(item.args) >= 2
            and isinstance(item.args[1], ast.Constant)
        ):
            existentes.add(item.args[1].value)

    adaptador = Sliders(existentes)
    arvore = adaptador.visit(arvore)

    if adaptador.eixos != {"x", "y"}:
        raise RuntimeError(
            "Campos de posição não reconhecidos. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)
    alterados["central_replay.py"] = (
        ast.unparse(arvore) + "\n"
    )

    arvore = HelpLabels().visit(ast.parse(
        (pasta / "ajuda_replay.py").read_text(
            encoding="utf-8-sig"
        )
    ))

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
                topico[0] == "Posição e atalhos das camadas"
                for topico in topicos
            ):
                topicos.append((
                    "Posição e atalhos das camadas",
                    (
                        "Na aba Posição do painel direito, "
                        "arraste as barras das margens X e Y. "
                        "Os campos numéricos continuam disponíveis "
                        "e sincronizados.\n\n"
                        "As margens são medidas a partir do canto "
                        "selecionado. A posição visível é limitada "
                        "pela área disponível. As barras usam a "
                        "resolução da tela; valores maiores podem "
                        "ser digitados nos campos.\n\n"
                        "Salvar configurações preserva as margens.\n\n"
                        "Atalhos padrão:\n"
                        "Ctrl+Alt+Shift+1: Terreno\n"
                        "Ctrl+Alt+Shift+2: Deslocamentos\n"
                        "Ctrl+Alt+Shift+3: Construções\n"
                        "Ctrl+Alt+Shift+4: Pesquisas e eras\n"
                        "Ctrl+Alt+Shift+5: Gaia\n"
                        "Ctrl+Alt+Shift+6: Ocultar militares\n"
                        "Ctrl+Alt+Shift+7: Ocultar econômicas\n"
                        "Ctrl+Alt+Shift+8: Ocultar casas\n\n"
                        "Cada atalho inverte o estado do respectivo "
                        "interruptor. Configure em Atalhos; um campo "
                        "vazio desativa a combinação.\n\n"
                        "Se um padrão conflitar com um atalho "
                        "anteriormente salvo, a nova combinação "
                        "começa desativada. As teclas do painel "
                        "econômico/militar e de seleção de jogadores "
                        "continuam disponíveis."
                    ),
                ))

            item.value = ast.parse(
                repr(topicos), mode="eval"
            ).body

    ast.fix_missing_locations(arvore)
    alterados["ajuda_replay.py"] = (
        ast.unparse(arvore) + "\n"
    )

    alterados["painel_horizontal.py"] = (
        (pasta / "painel_horizontal.py").read_text(
            encoding="utf-8-sig"
        ).replace(
            "Atalhos · jogadores e painel",
            "Atalhos · jogadores, painel e camadas",
        )
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

    print("\nPosição, botões AJUDA e atalhos preparados.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.9 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)