import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r'''
import base64
import copy
import math
import xml.etree.ElementTree as ET


ART = {
    "boar": (
        '<ellipse cx="24" cy="27" rx="17" ry="12" fill="#895b39"/>'
        '<path d="M12 19L13 8L22 17M29 17L37 9L37 22" fill="#68432e"/>'
        '<ellipse cx="34" cy="31" rx="9" ry="7" fill="#bb8d67"/>'
        '<circle cx="35" cy="29" r="1.5" fill="#38251d"/>'
        '<path d="M27 34Q23 42 21 33M39 35Q43 40 42 31" '
        'fill="none" stroke="#f4e6c7" stroke-width="3"/>'
        '<circle cx="25" cy="23" r="2" fill="#101716"/>'
    ),
    "deer": (
        '<path d="M19 18L9 7M13 12L12 3M13 12L4 12'
        'M29 18L39 7M35 12L36 3M35 12L44 12" '
        'fill="none" stroke="#dbc49b" stroke-width="2.5"/>'
        '<path d="M18 22L6 19L12 28M30 22L42 19L36 28" fill="#c48e58"/>'
        '<path d="M15 19Q24 13 33 19L30 39Q24 45 18 39Z" fill="#c89158"/>'
        '<ellipse cx="24" cy="36" rx="6" ry="5" fill="#e2c6a0"/>'
        '<circle cx="19" cy="27" r="1.5"/>'
        '<circle cx="29" cy="27" r="1.5"/>'
        '<ellipse cx="24" cy="36" rx="3" ry="2" fill="#30251c"/>'
    ),
    "sheep": (
        '<g fill="#e4dfcf">'
        '<circle cx="14" cy="19" r="9"/>'
        '<circle cx="23" cy="14" r="10"/>'
        '<circle cx="34" cy="19" r="9"/>'
        '<circle cx="15" cy="29" r="9"/>'
        '<circle cx="32" cy="29" r="9"/></g>'
        '<ellipse cx="24" cy="29" rx="8" ry="12" fill="#5a5143"/>'
        '<path d="M18 24L8 22M30 24L40 22" '
        'stroke="#5a5143" stroke-width="5"/>'
        '<circle cx="21" cy="27" r="1.4" fill="white"/>'
        '<circle cx="27" cy="27" r="1.4" fill="white"/>'
    ),
    "cow": (
        '<path d="M15 19Q4 18 8 7Q10 16 20 14'
        'M33 19Q44 18 40 7Q38 16 28 14" fill="#e8d7ad"/>'
        '<path d="M15 20L5 19L10 28M33 20L43 19L38 28" fill="#a56e43"/>'
        '<path d="M14 16Q24 10 34 16L33 37Q24 45 15 37Z" fill="#a56e43"/>'
        '<path d="M20 14L26 13L25 31L21 30Z" fill="#e8dac2"/>'
        '<ellipse cx="24" cy="36" rx="10" ry="6" fill="#d9b18a"/>'
        '<circle cx="19" cy="26" r="1.7"/>'
        '<circle cx="30" cy="26" r="1.7"/>'
        '<circle cx="20" cy="36" r="1.3"/>'
        '<circle cx="28" cy="36" r="1.3"/>'
    ),
    "goat": (
        '<path d="M18 21Q6 7 16 4M30 21Q42 7 32 4" '
        'fill="none" stroke="#b39465" stroke-width="4"/>'
        '<path d="M17 22L6 18L11 29M31 22L42 18L37 29" fill="#d6c4a0"/>'
        '<path d="M15 18L33 18L31 36L24 44L17 36Z" fill="#e1d3b7"/>'
        '<path d="M20 35L28 35L24 45Z" fill="#ac956d"/>'
        '<circle cx="19" cy="27" r="1.5"/>'
        '<circle cx="29" cy="27" r="1.5"/>'
    ),
    "wolf": (
        '<path d="M10 28L9 6L21 17L28 17L40 6L38 30L24 44Z" fill="#a9afa7"/>'
        '<path d="M12 14L19 23L15 27M36 14L29 23L33 27" fill="#626e68"/>'
        '<path d="M14 30L24 24L34 30L29 39L19 39Z" fill="#dfdfcc"/>'
        '<circle cx="17" cy="26" r="2" fill="#d9ba52"/>'
        '<circle cx="31" cy="26" r="2" fill="#d9ba52"/>'
        '<path d="M19 35L29 35L24 40Z" fill="#252c29"/>'
    ),
    "cat": (
        '<circle cx="12" cy="15" r="7" fill="#a87e38"/>'
        '<circle cx="36" cy="15" r="7" fill="#a87e38"/>'
        '<ellipse cx="24" cy="27" rx="17" ry="15" fill="#d3ab57"/>'
        '<g fill="#443b27">'
        '<circle cx="14" cy="22" r="2"/>'
        '<circle cx="34" cy="22" r="2"/>'
        '<circle cx="24" cy="18" r="2"/></g>'
        '<ellipse cx="24" cy="34" rx="9" ry="6" fill="#e5d1a0"/>'
        '<circle cx="17" cy="28" r="1.7"/>'
        '<circle cx="31" cy="28" r="1.7"/>'
        '<path d="M21 32L27 32L24 36Z" fill="#4a3a2c"/>'
    ),
    "elephant": (
        '<ellipse cx="12" cy="24" rx="10" ry="15" fill="#7d8b87"/>'
        '<ellipse cx="36" cy="24" rx="10" ry="15" fill="#7d8b87"/>'
        '<ellipse cx="24" cy="22" rx="12" ry="16" fill="#a1aaa1"/>'
        '<path d="M20 28L20 41Q29 48 32 37" '
        'fill="none" stroke="#a1aaa1" stroke-width="8"/>'
        '<path d="M15 29L12 38L19 33M33 29L36 38L29 33" fill="#e5ddbd"/>'
        '<circle cx="18" cy="23" r="1.5"/>'
        '<circle cx="30" cy="23" r="1.5"/>'
    ),
    "rhino": (
        '<ellipse cx="23" cy="28" rx="18" ry="13" fill="#929b8e"/>'
        '<path d="M14 21L11 7L23 19M28 19L34 9L36 24" fill="#717d73"/>'
        '<path d="M29 31L35 7L41 34Z" fill="#e1d5b3"/>'
        '<circle cx="20" cy="25" r="2"/>'
    ),
    "bird": (
        '<path d="M7 33Q12 12 29 13Q40 14 36 29L27 35L15 42Z" fill="#a88e5b"/>'
        '<path d="M27 16L44 22L32 26" fill="#e0bc62"/>'
        '<path d="M10 34Q16 22 27 29L16 40Z" fill="#6d6146"/>'
        '<circle cx="29" cy="20" r="2" fill="#17201b"/>'
    ),
    "goose": (
        '<path d="M9 36Q11 28 22 28L23 16Q25 6 32 9'
        'Q41 12 35 22L30 26L30 35Q21 43 9 36Z" fill="#eee5d2"/>'
        '<path d="M34 14L45 19L34 22Z" fill="#e0a348"/>'
        '<circle cx="31" cy="15" r="1.5" fill="#1a2420"/>'
    ),
    "fish": (
        '<path d="M8 24Q23 6 37 24Q23 42 8 24L3 13L3 35Z" fill="#69a5ba"/>'
        '<path d="M16 14L24 8L28 16M16 34L24 40L28 32" fill="#9dbfb1"/>'
        '<circle cx="31" cy="22" r="2" fill="#182b2e"/>'
    ),
    "relic": (
        '<path d="M17 39L17 30L12 30L12 24L20 24L20 15'
        'L16 15L16 9L20 9L20 5L28 5L28 9L32 9L32 15'
        'L28 15L28 24L36 24L36 30L31 30L31 39Z" fill="#dbb45d"/>'
        '<path d="M12 39L36 39L39 44L9 44Z" fill="#a8843c"/>'
    ),
    "neutral": (
        '<g fill="#c9bf9e">'
        '<ellipse cx="24" cy="32" rx="12" ry="9"/>'
        '<ellipse cx="10" cy="20" rx="5" ry="7"/>'
        '<ellipse cx="20" cy="12" rx="5" ry="7"/>'
        '<ellipse cx="31" cy="13" rx="5" ry="7"/>'
        '<ellipse cx="39" cy="22" rx="5" ry="7"/></g>'
    ),
}


def ativar(g):
    if g.get("_gaia_minimapa_ativa"):
        return
    g["_gaia_minimapa_ativa"] = True

    t, mini, app = g["t"], g["mini"], g["app"]
    ns = g["NS"]
    g["p"].CONFIG_DEFAULTS.update(gaia_show=True)
    visible = [True]

    def records(session):
        seen = set()
        result = []
        dimension = session.model["dimension"]

        for player in session.header["players"]:
            if player["number"] != 0:
                continue

            for obj in player["objects"]:
                ident = obj["object_id"]
                instance = obj["instance_id"]

                if obj["class_id"] != 70:
                    continue
                if instance in seen:
                    continue

                x = obj["position"]["x"]
                y = obj["position"]["y"]

                if not all(
                    isinstance(value, (int, float))
                    and math.isfinite(value)
                    and 0 <= value < dimension
                    for value in (x, y)
                ):
                    continue

                seen.add(instance)
                result.append(dict(
                    id=instance,
                    owner=0,
                    type_id=ident,
                    kind="unit",
                    x=x,
                    y=y,
                    name=(
                        session.reference["objects"].get(str(ident))
                        or f"ID {ident}"
                    ),
                ))

        return result

    def kind(obj):
        name = obj["name"].lower()
        ident = obj["type_id"]

        if ident == 285 or "relic" in name:
            return "relic"
        if ident in app.base.g.FISH_IDS:
            return "fish"

        catalog = [
            (("boar", "javelina"), "boar"),
            (("sheep",), "sheep"),
            (("cow", "buffalo", "zebu"), "cow"),
            (("goat", "ibex"), "goat"),
            (("deer", "gazelle"), "deer"),
            (("wolf", "fox"), "wolf"),
            (("jaguar", "lion", "leopard", "tiger"), "cat"),
            (("elephant",), "elephant"),
            (("rhinoceros", "rhino"), "rhino"),
            (("goose", "duck", "turkey"), "goose"),
            (("hawk", "eagle", "stork", "vulture", "ostrich"), "bird"),
        ]

        for words, icon in catalog:
            if any(word in name for word in words):
                return icon

        return "neutral"

    def clusters(objects):
        groups = []

        for obj in objects:
            group = next(
                (
                    existing
                    for existing in groups
                    if existing[0]["type_id"] == obj["type_id"]
                    and any(
                        (member["x"] - obj["x"]) ** 2
                        + (member["y"] - obj["y"]) ** 2 <= 9
                        for member in existing
                    )
                ),
                None,
            )

            if group is None:
                groups.append([obj])
            else:
                group.append(obj)

        return groups

    old_prepare = t.ICONS.prepare

    def prepare(session):
        proxy = copy.copy(session)
        proxy.initial = list(session.initial) + records(session)
        old_prepare(proxy)

    t.ICONS.prepare = prepare
    old_render = app.map_svg

    def render(session):
        neutral = records(session)
        ids = {obj["id"] for obj in neutral}

        proxy = copy.copy(session)
        proxy.model = dict(session.model)
        proxy.model["points"] = [
            obj for obj in session.model["points"]
            if obj.get("instance") not in ids
        ]
        proxy.initial = [
            obj for obj in session.initial
            if obj["owner"] != 0
        ]

        root = ET.fromstring(old_render(proxy))

        if not visible[0]:
            return ET.tostring(root, encoding="unicode")

        layer = root.find(
            "{" + ns + '}g[@clip-path="url(#map-area)"]'
        )
        defs = root.find("{" + ns + "}defs")

        if layer is None or defs is None:
            return ET.tostring(root, encoding="unicode")

        options = (
            t._projection_context.options
            or mini.SETTINGS[:2]
        )
        size = t.OPTIONS[3]
        embedded = set()

        for group in clusters(neutral):
            obj = group[0]
            ident = obj["type_id"]
            key = f"gaia-icon-{ident}"

            if ident not in embedded:
                symbol = ET.SubElement(
                    defs, "{" + ns + "}g", {"id": key}
                )

                ET.SubElement(
                    symbol, "{" + ns + "}rect",
                    {
                        "x": "0", "y": "0",
                        "width": "48", "height": "48",
                        "rx": "5", "fill": "#252c24",
                    },
                )

                raw = t.ICONS.images.get(ident)

                if raw:
                    ET.SubElement(
                        symbol, "{" + ns + "}image",
                        {
                            "width": "48", "height": "48",
                            "href": (
                                "data:image/png;base64,"
                                + base64.b64encode(raw).decode()
                            ),
                        },
                    )
                else:
                    art = ET.fromstring(
                        '<g xmlns="' + ns + '">'
                        + ART[kind(obj)] + "</g>"
                    )
                    symbol.append(art)

                ET.SubElement(
                    symbol, "{" + ns + "}rect",
                    {
                        "x": ".5", "y": ".5",
                        "width": "47", "height": "47",
                        "rx": "5", "fill": "none",
                        "stroke": "#c3b186",
                        "stroke-width": "1",
                    },
                )
                embedded.add(ident)

            x = sum(member["x"] for member in group) / len(group)
            y = sum(member["y"] for member in group) / len(group)

            px, py = t._projection(
                x, y, session.model["dimension"],
                options[0], options[1],
            )

            node = ET.SubElement(
                layer, "{" + ns + "}g",
                {
                    "data-gaia": str(ident),
                    "data-count": str(len(group)),
                },
            )

            ET.SubElement(
                node, "{" + ns + "}title"
            ).text = (
                f"Gaia inicial · {obj['name']} · "
                f"{len(group)} objeto(s). "
                "Posição e propriedade atuais não confirmadas."
            )

            picture = ET.SubElement(
                node, "{" + ns + "}g",
                {
                    "transform": (
                        f"translate({px-size/2} {py-size/2}) "
                        f"scale({size/48})"
                    )
                },
            )
            ET.SubElement(
                picture, "{" + ns + "}use",
                {"href": "#" + key},
            )

            if len(group) > 1:
                width = 5 * len(str(len(group))) + 4

                ET.SubElement(
                    node, "{" + ns + "}rect",
                    {
                        "x": str(px + size/2 - width),
                        "y": str(py + size/2 - 9),
                        "width": str(width),
                        "height": "11",
                        "rx": "2",
                        "fill": "#1d2521",
                    },
                )
                ET.SubElement(
                    node, "{" + ns + "}text",
                    {
                        "x": str(px + size/2 - 2),
                        "y": str(py + size/2),
                        "font-size": "9",
                        "text-anchor": "end",
                        "fill": "white",
                        "font-family": "Segoe UI,Arial",
                    },
                ).text = str(len(group))

        return ET.tostring(root, encoding="unicode")

    app.map_svg = render
    mini.minimap_svg = render
    g["selected_map"] = render

    Base = g["Window"]

    class Window(Base):
        def setup_position_controls(self, parent):
            super().setup_position_controls(parent)

            import tkinter as tk
            self.gaia_show = tk.BooleanVar(value=True)
            self.gaia_show.trace_add(
                "write", self.gaia_options
            )

        def gaia_options(self, *args):
            visible[0] = bool(self.gaia_show.get())
            self.next_frame = 0

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.gaia_options()

    g["Window"] = Window
    g["gaia_records"] = records
'''


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

            if "gaia_minimapa.py" not in nomes:
                node.elts.append(
                    ast.Constant("gaia_minimapa.py")
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
                + ". Execute na pasta completa da central de replay."
            )

    alterados = {"gaia_minimapa.py": MODULO.lstrip()}

    texto = (pasta / "painel_jogadores.py").read_text(
        encoding="utf-8-sig"
    )

    if "_ativar_gaia_minimapa(globals())" not in texto:
        integracao = (
            "from gaia_minimapa import ativar "
            "as _ativar_gaia_minimapa\n"
            "_ativar_gaia_minimapa(globals())\n\n"
        )

        texto, quantidade = re.subn(
            r"(?m)^from central_replay import ativar.*$",
            lambda resultado: integracao + resultado.group(),
            texto,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Integração da central não reconhecida. "
                "Nenhum arquivo foi alterado."
            )

    alterados["painel_jogadores.py"] = texto

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
                        isinstance(item, ast.Attribute)
                        and item.attr == "gaia_show"
                        for item in ast.walk(metodo)
                    )

                    if not existe:
                        metodo.body.extend(ast.parse(
                            'self.switch(other, "Gaia", self.gaia_show)'
                        ).body)

    if quantidade != 1:
        raise RuntimeError(
            "Controles da central não reconhecidos."
        )

    ast.fix_missing_locations(arvore)
    alterados["central_replay.py"] = ast.unparse(arvore) + "\n"

    adaptador = Build()
    arvore = adaptador.visit(ast.parse(
        (pasta / "gerar_instalador.py").read_text(
            encoding="utf-8-sig"
        )
    ))

    if not adaptador.encontrou:
        raise RuntimeError("Gerador diferente do esperado.")

    ast.fix_missing_locations(arvore)
    alterados["gerar_instalador.py"] = ast.unparse(arvore) + "\n"

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
                    topico[0] == "Gaia no minimapa"
                    for topico in topicos
                ):
                    topicos.append((
                        "Gaia no minimapa",
                        (
                            "A camada Gaia mostra os animais, relíquias "
                            "e outras unidades neutras presentes no "
                            "estado inicial.\n\n"
                            "Use o interruptor Gaia para mostrar ou "
                            "ocultar esses ícones. O tamanho acompanha "
                            "os ícones das tropas, na seção Minimapa.\n\n"
                            "Objetos próximos do mesmo tipo são "
                            "agrupados; o número indica a quantidade "
                            "inicial naquele grupo.\n\n"
                            "A fauna usa ícones ilustrativos no formato "
                            "dos demais ícones. Unidades com ícone do "
                            "jogo disponível reutilizam esse ícone. "
                            "Tipos sem identificação usam um símbolo "
                            "neutro.\n\n"
                            "O filtro de jogadores não remove Gaia. "
                            "Capturas, mortes e posições posteriores "
                            "não são confirmadas pela fonte atual."
                        ),
                    ))

                item.value = ast.parse(
                    repr(topicos), mode="eval"
                ).body

        ast.fix_missing_locations(arvore)
        alterados["ajuda_replay.py"] = ast.unparse(arvore) + "\n"

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

    print("\nGaia adicionada ao minimapa e às camadas.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.4 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)