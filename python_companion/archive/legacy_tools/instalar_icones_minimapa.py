"""Adiciona os ícones das construções ao minimapa."""
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request


COMMIT = "e56728e76b7d08301fba7b18d5f16bc8554c109a"
SOURCE = (
    "https://raw.githubusercontent.com/"
    f"SiegeEngineers/aoe2techtree/{COMMIT}/"
)

ASSETS = [
    (12, 'Barracks', 2, '4198a60591b17fda07b48b57cbad43e6620e3618867882138d1fed39774352b0'),
    (45, 'Dock', 13, '17ba0932215f01f44ec42f1a7bb9964d742c11e9c3ba6de3bb38e3527532d4e9'),
    (49, 'Siege Workshop', 22, 'a63ed7edbc550b7916fe2213c7e7b890ba704a0c3624f7e207b7d9c461746f65'),
    (50, 'Farm', 35, '9ff16a07492cc8fb9f8c51cbad0444d5218e6637f785a261b6629db257e2e4c9'),
    (68, 'Mill', 19, '56578ebb5a4f4ae6de215fe0b2b7185d596be20a64995c069a336f50d718a411'),
    (70, 'House', 34, '1f983df1d738199517749225dfc19919cf689658653b8cdabffcbb0b2471a7e9'),
    (72, 'Palisade Wall', 30, 'af8ed44884e52834e7c653d5e51d5baa8fae9b053b1eae9df1755b392c5a824c'),
    (79, 'Watch Tower', 25, 'c37be6753f9d8e4d41b892a747f769b64728ba9737b55801eaf6faf83db0a1ef'),
    (82, 'Castle', 7, '701d9fc3add461d23ed2bbe244172e1a5dec903bed113000c498435441dc80c9'),
    (84, 'Market', 16, 'efd5891419d4faefb62556dd70e31884dd3457bba26a4eb89aec123588d92671'),
    (87, 'Archery Range', 0, '481171f30ac2314bce39b9ebc3c020339e2452a1b091df03546e024d34a7b257'),
    (101, 'Stable', 23, '547b2cf7771cdda392ef1fe9724f0ebc4fafa2669fb755a59681f61e2a23860c'),
    (103, 'Blacksmith', 4, 'a4b7228e1e6ad9fee113a304e6edf761b7b5bf9993e86cc0f2b5ccf1246aedf9'),
    (104, 'Monastery', 10, '18c4b8e689b93be80e9c4002fb1c9bc08238dbdba90b755b2a04d4926290caf9'),
    (109, 'Town Center', 28, '5c8e27c91b9b4950f3adf9cefbdacae56378a982a7d5eec1c65d8763ad88e7d2'),
    (117, 'Stone Wall', 31, '433b80339e0a18970e037fb61a69cf1ad5a6a7092da73e9cb3a3523f274f03e3'),
    (155, 'Fortified Wall', 32, '143314d165b1589190d90b0a8498c861894bac5c46122226c521a62093d158d3'),
    (209, 'University', 33, 'fefd3e8029471cfe39f3b509771278fdeb2f56cd2927124940196e3424f732cd'),
    (234, 'Guard Tower', 27, '1b9c6d4f3139fc5e01b14845a182f06ee8291ed38ceaeb192c68bebea0821fea'),
    (235, 'Keep', 26, '633f03ce6a6eeef9c5aa64b0252c5f24b20cfbc39bd18cd11c6ef3b280597fbe'),
    (236, 'Bombard Tower', 42, '5a15323cb0e721ca92b533516883361917dc0965e2aef9d5dfecb89bb0452c20'),
    (276, 'Wonder', 37, '8d2574d4e0a35e64d93f77138279b88ffb6baa9f7e0f67209aede7412cfdf87d'),
    (487, 'Gate', 36, 'e690f682bff8af4b5bbcfec37e8652686d3f9e3e78eee1138628215e6aa06101'),
    (562, 'Lumber Camp', 40, '074c3a229b4e96f38aec5c86ff26ff93217c2b62b50954a06d66e6ab817a905b'),
    (584, 'Mining Camp', 39, '71f4f0c451a8d9428b3ad070667919560815aa80435b65e931ca393e42a4f559'),
    (598, 'Outpost', 38, '3e8e1884ed4adb98b5dc6499039b5f4c2363cd4f6e5cf84e6adf51368c18b287'),
    (621, 'Town Center', 28, '5c8e27c91b9b4950f3adf9cefbdacae56378a982a7d5eec1c65d8763ad88e7d2'),
    (792, 'Palisade Gate', 44, '9f85f5b6a2d1a6fcd009d4b3a8ae540f3cda9e02c1131f1e22b0a03e280c46c5'),
    (1021, 'Feitoria', 53, '28bd7cf35d84871e268dc2db3ee42b07736fb74c42e5074035689a4357da7bdf'),
    (1251, 'Krepost', 55, '16147710606ff362e40d4ba292b1e7fc15f2d85f5df5933e919e54241c4044db'),
    (1665, 'Donjon', 84, '28d3d10bac386ba1ad535fb1ae774ab800b9201077450a85f4f1e7dc1bdbd1b2'),
    (1734, 'Folwark', 86, '538d52ae4c065a8d8790c1ca846d92388ceb7d96d5f8659c389f48fb48888139'),
    (1754, 'Caravanserai', 87, 'd2167ff8661e84a888f41821f9fa979e8afe81d4395800036c0321c3d30a6fc0'),
    (1806, 'Fortified Church', 88, '79b181b60d7d75cc8d10b584a6d4add129742d0114c37eca19e2461fe782ef1e'),
    (1808, 'Mule Cart', 89, '8b51b0d02a4086af34e9f641964f00c5d28073b1ae9f6bdcbdab87aa9a1d51e7'),
    (1889, 'Pasture', 96, 'cd90e723e1f7278bfa0f674ae340dc515cb98d8807912628a546bd0ad3b5ea63'),
    (2556, 'Settlement', 98, '16319412f5414f66ab47b4bc4884d73dfc69d2a283efe924c1651fbcb0bb78aa'),
]


SUPPORT = r'''
# ICONES_CONSTRUCOES_MINIMAPA_V1
MAP_BUILDING_ICONS = __CATALOG__
MAP_ICON_SIZE = 24


def minimap_svg(session):
    import base64
    from pathlib import Path
    from types import SimpleNamespace

    options = SETTINGS
    model = dict(session.model)
    model["points"] = [
        p for p in session.model["points"]
        if p["kind"] != "centros"
    ]

    proxy = SimpleNamespace(
        model=model,
        header=session.header,
        initial=[
            o for o in session.initial
            if o["kind"] == "unit"
        ],
        build_requests=(),
    )

    root = ET.fromstring(
        _minimap_without_buildings(proxy, options)
    )
    layer = root.find(
        "{" + NS + '}g[@clip-path="url(#map-area)"]'
    )
    defs = root.find("{" + NS + "}defs")

    if layer is None or defs is None:
        raise RuntimeError(
            "A versão do minimapa não contém a camada esperada."
        )

    def add(parent, tag, **attrs):
        return ET.SubElement(
            parent,
            "{" + NS + "}" + tag,
            {k: str(v) for k, v in attrs.items()},
        )

    n = session.model["dimension"]

    def valid(x, y):
        return (
            isinstance(x, (int, float))
            and isinstance(y, (int, float))
            and 0 <= x < n
            and 0 <= y < n
        )

    colors = {
        p["number"]: p["color_id"]
        for p in session.header.get("de", {}).get("players", [])
        if (
            p.get("number", -1) > 0
            and 0 <= p.get("color_id", -1) < 8
        )
    }

    def owner_color(owner):
        fallback = (
            owner - 1
            if isinstance(owner, int) and owner > 0
            else 6
        )
        index = colors.get(owner, fallback)
        return PLAYER_COLORS[index % len(PLAYER_COLORS)]

    names = {
        value[0].casefold(): ident
        for ident, value in MAP_BUILDING_ICONS.items()
    }
    cache = {}

    def image_id(ident):
        if ident not in MAP_BUILDING_ICONS:
            name = session.reference.get(
                "objects", {}
            ).get(str(ident), "")
            ident = names.get(str(name).casefold())

        if ident not in MAP_BUILDING_ICONS:
            return None

        if ident in cache:
            return cache[ident]

        path = (
            Path(__file__).resolve().parent
            / "icones_aoe2"
            / MAP_BUILDING_ICONS[ident][1]
        )

        try:
            data = path.read_bytes()
        except OSError:
            cache[ident] = None
            return None

        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            cache[ident] = None
            return None

        key = f"map-building-{ident}"
        add(
            defs,
            "image",
            id=key,
            width=48,
            height=48,
            href=(
                "data:image/png;base64,"
                + base64.b64encode(data).decode("ascii")
            ),
        )

        cache[ident] = key
        return key

    markers = {}

    def register(owner, ident, x, y, pending):
        if not valid(x, y):
            return
        key = owner, ident, round(x, 3), round(y, 3)
        markers[key] = owner, ident, x, y, pending

    for obj in session.initial:
        if obj["kind"] == "building":
            register(
                obj["owner"],
                obj["type_id"],
                obj["x"],
                obj["y"],
                False,
            )

    for point in session.model["points"]:
        if point["kind"] != "centros":
            continue

        already_present = any(
            owner == point["owner"]
            and abs(x - point["x"]) < .01
            and abs(y - point["y"]) < .01
            for owner, ident, x, y, pending
            in markers.values()
        )

        if not already_present:
            register(
                point["owner"],
                point["id"],
                point["x"],
                point["y"],
                False,
            )

    for event in session.build_requests:
        ident = event.get("building_id")
        if isinstance(ident, int):
            register(
                event.get("player"),
                ident,
                event.get("x"),
                event.get("y"),
                True,
            )

    for owner, ident, x, y, pending in markers.values():
        px, py = project(
            x, y, n, options[0], options[1]
        )
        size = MAP_ICON_SIZE

        node = add(
            layer,
            "g",
            **{
                "data-building-id": ident,
                "data-kind": "order" if pending else "initial",
                "data-owner": owner,
                "data-map-x": px,
                "data-map-y": py,
            },
        )

        add(node, "title").text = (
            f"J{owner}: pedido de construção; "
            "conclusão não confirmada."
            if pending
            else
            f"J{owner}: construção no estado inicial do replay."
        )

        key = image_id(ident)

        if key:
            add(
                node,
                "rect",
                x=px - size / 2 - 1,
                y=py - size / 2 - 1,
                width=size + 2,
                height=size + 2,
                fill="none",
                stroke=owner_color(owner),
                **{"stroke-width": 1},
            )

            scaled = add(
                node,
                "g",
                transform=(
                    f"translate({px-size/2} {py-size/2}) "
                    f"scale({size/48})"
                ),
            )
            add(scaled, "use", href="#" + key)

        else:
            add(
                node,
                "text",
                x=px,
                y=py + 5,
                fill=owner_color(owner),
                **{
                    "font-size": 18,
                    "text-anchor": "middle",
                },
            ).text = "?"

        if pending:
            add(
                node,
                "text",
                x=px + size / 2 - 4,
                y=py - size / 2 + 8,
                fill="white",
                **{
                    "font-family": "Segoe UI,Arial",
                    "font-size": 12,
                    "font-weight": "bold",
                },
            ).text = "?"

        if ident in app.base.g.TC_IDS:
            add(
                node,
                "text",
                x=px + size / 2 + 3,
                y=py - size / 2 - 3,
                fill="white",
                **{
                    "font-family": "Segoe UI,Arial",
                    "font-size": 14,
                    "font-weight": "bold",
                },
            ).text = f"J{owner}"

    return ET.tostring(root, encoding="unicode")

'''


class SnapshotOptions(ast.NodeTransformer):
    def visit_Name(self, node):
        if node.id == "SETTINGS":
            node.id = "_options"
        return node


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, name = tempfile.mkstemp(
        prefix=".aoe2-",
        suffix=".tmp",
        dir=path.parent,
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install():
    folder = Path(__file__).resolve().parent
    target = folder / "minimapa_aoe2.py"

    if not target.exists():
        raise RuntimeError(
            "Coloque o instalador na mesma pasta "
            "de minimapa_aoe2.py."
        )

    source = target.read_text(encoding="utf-8-sig")
    installed = (
        "# ICONES_CONSTRUCOES_MINIMAPA_V1" in source
    )

    if not installed:
        tree = ast.parse(source)
        node = next(
            (
                item for item in tree.body
                if isinstance(item, ast.FunctionDef)
                and item.name == "minimap_svg"
            ),
            None,
        )

        if (
            node is None
            or "map-area" not in ast.get_source_segment(
                source, node
            )
        ):
            raise RuntimeError(
                "É necessária a versão do minimapa "
                "com moldura e orientação ajustável."
            )

        start = node.lineno - 1
        end = node.end_lineno

        node.name = "_minimap_without_buildings"
        node.args.args.append(
            ast.arg(arg="_options")
        )
        node = ast.fix_missing_locations(
            SnapshotOptions().visit(node)
        )

        metadata = {
            ident: (name, f"building_{ident}.png")
            for ident, name, picture, digest in ASSETS
        }

        replacement = (
            ast.unparse(node)
            + "\n\n"
            + SUPPORT.replace(
                "__CATALOG__", repr(metadata)
            )
        )

        lines = source.splitlines(keepends=True)
        lines[start:end] = [replacement]
        updated = "".join(lines)

        compile(updated, str(target), "exec")

    manifest = {}

    for ident, name, picture, digest in ASSETS:
        path = (
            folder / "icones_aoe2"
            / f"building_{ident}.png"
        )
        data = path.read_bytes() if path.exists() else b""
        url = SOURCE + f"img/Building/{picture}.png"

        if hashlib.sha256(data).hexdigest() != digest:
            print("Baixando:", name)

            with urllib.request.urlopen(
                url, timeout=30
            ) as response:
                data = response.read(256 * 1024 + 1)

            if (
                hashlib.sha256(data).hexdigest() != digest
                or not data.startswith(b"\x89PNG\r\n\x1a\n")
            ):
                raise RuntimeError(
                    "Ícone inválido: " + name
                )

            atomic_write(path, data)

        manifest[str(ident)] = {
            "name": name,
            "url": url,
            "sha256": digest,
        }

    atomic_write(
        folder / "icones_aoe2" / "origem_minimapa.json",
        json.dumps(
            manifest, ensure_ascii=False, indent=2
        ).encode("utf-8"),
    )

    atomic_write(
        folder / "icones_aoe2" / "CREDITOS_MINIMAPA.txt",
        (
            "Fonte: SiegeEngineers/aoe2techtree\n"
            "Age of Empires II © Microsoft Corporation.\n"
            "Game Icons © Hidden Path Entertainment, "
            "Forgotten Empires, SkyBox Labs, Ensemble Studios.\n"
            "https://github.com/SiegeEngineers/aoe2techtree\n"
        ).encode("utf-8"),
    )

    if not installed:
        backup = target.with_name(
            "minimapa_aoe2.antes_icones_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".py"
        )
        shutil.copy2(target, backup)
        atomic_write(
            target, updated.encode("utf-8")
        )
        print("Backup:", backup.name)

    print(
        "Ícones instalados no minimapa. "
        "Abra painel_aoe2.py normalmente."
    )


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print("Não foi possível instalar:", exc)
        raise SystemExit(1)