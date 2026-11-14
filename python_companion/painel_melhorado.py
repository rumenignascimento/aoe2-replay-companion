"""Paliçadas em linhas e pesquisas agrupadas por construção."""
from collections import defaultdict
from fractions import Fraction
import json
import math
import tkinter as tk
from tkinter import ttk
import time
import urllib.request
import xml.etree.ElementTree as ET

import painel_tropas as t


p = t.panel
app = t.app
mini = t.mini
NS = t.NS

# Pesquisas na barra; possíveis extremidades abertas.
VIEW = (True, True)


def is_farm(session, ident):
    name = session.reference.get(
        "objects", {}
    ).get(str(ident), "")
    return ident == 50 or str(name).casefold() == "farm"


def is_palisade(session, ident):
    name = session.reference.get(
        "objects", {}
    ).get(str(ident), "")
    return (
        ident == 72
        or str(name).casefold() == "palisade wall"
    )


def raster_line(a, b):
    x, y = a
    xx, yy = b
    dx, dy = abs(xx - x), abs(yy - y)
    sx = 1 if x < xx else -1
    sy = 1 if y < yy else -1
    error = dx - dy

    while True:
        yield x, y
        if (x, y) == (xx, yy):
            break
        double = 2 * error
        if double > -dy:
            error -= dy
            x += sx
        if double < dx:
            error += dx
            y += sy


# Aproximações de ocupação no terreno.
# Portões e cantos do centro urbano não são completamente modelados.
FOOTPRINTS = {
    12: 3, 45: 3, 49: 4, 68: 2, 70: 2,
    79: 1, 82: 4, 84: 4, 87: 3, 101: 3,
    103: 3, 104: 3, 109: 4, 209: 4,
    234: 1, 235: 1, 236: 2, 276: 5,
    487: 1, 562: 2, 584: 2, 598: 1,
    621: 4, 792: 1, 1021: 3, 1251: 3,
    1665: 2, 1734: 3, 1754: 3,
    1806: 3, 2556: 4,
}


def wall_geometry(session):
    n = session.model["dimension"]
    cells = {}
    obstacles = set()

    def valid(x, y):
        return (
            isinstance(x, (int, float))
            and isinstance(y, (int, float))
            and 0 <= x < n
            and 0 <= y < n
        )

    def cell(x, y):
        return math.floor(x), math.floor(y)

    def wall(owner, x, y, planned):
        if valid(x, y):
            cells[(owner, *cell(x, y))] = planned

    def obstacle(ident, x, y):
        if (
            not valid(x, y)
            or is_farm(session, ident)
            or is_palisade(session, ident)
        ):
            return

        size = FOOTPRINTS.get(ident, 1)
        lo_x = math.floor(x - size / 2 + .001)
        lo_y = math.floor(y - size / 2 + .001)

        for a in range(lo_x, lo_x + size):
            for b in range(lo_y, lo_y + size):
                obstacles.add((a, b))

    for point in session.model["points"]:
        if (
            point["kind"] in ("madeira", "ouro", "pedra")
            and valid(point["x"], point["y"])
        ):
            obstacles.add(cell(point["x"], point["y"]))

    for obj in session.initial:
        if obj["kind"] != "building":
            continue

        if is_palisade(session, obj["type_id"]):
            wall(
                obj["owner"], obj["x"], obj["y"], False
            )
        else:
            obstacle(
                obj["type_id"], obj["x"], obj["y"]
            )

    for event in session.build_requests:
        ident = event.get("building_id")
        x, y = event.get("x"), event.get("y")

        if not valid(x, y):
            continue

        if is_palisade(session, ident):
            if (
                event["action"] == "WALL"
                and valid(
                    event.get("x_end"),
                    event.get("y_end"),
                )
            ):
                for a, b in raster_line(
                    cell(x, y),
                    cell(event["x_end"], event["y_end"]),
                ):
                    wall(
                        event.get("player"),
                        a + .5,
                        b + .5,
                        True,
                    )
            else:
                wall(
                    event.get("player"), x, y, True
                )
        else:
            obstacle(ident, x, y)

    edges = []
    ends = []
    owners = {key[0] for key in cells}

    for key, planned in cells.items():
        owner, x, y = key
        neighbors = []

        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                other = (owner, x + dx, y + dy)

                if not (dx or dy) or other not in cells:
                    continue

                if dx and dy and (
                    (owner, x + dx, y) in cells
                    or (owner, x, y + dy) in cells
                ):
                    continue

                neighbors.append(other)

                if (x, y) < (x + dx, y + dy):
                    edges.append((
                        key,
                        other,
                        planned or cells[other],
                    ))

        if not neighbors:
            edges.append((key, None, planned))

        linked = any(
            (x + dx, y + dy) in obstacles
            or any(
                (other_owner, x + dx, y + dy) in cells
                for other_owner in owners
                if other_owner != owner
            )
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if dx or dy
        )

        if len(neighbors) < 2 and not linked:
            ends.append(key)

    return edges, ends


class ResearchIcons:
    def __init__(self):
        self.key = None
        self.tech = {}
        self.buildings = {}
        self.paths = {}
        self.attempted = set()
        self.errors = []

    def prepare(self, session):
        t.ICONS.prepare(session)

        civ = next(
            (
                a["civilization"]
                for a in session.model["players"]
                if a["slot"] == 2
            ),
            "BRITONS",
        )
        key = str(civ)

        if self.key != key:
            self.key = key
            self.tech = {}
            self.buildings = {}

            for name in ("BRITONS", str(civ).upper()):
                import re

                safe = re.sub("[^A-Z]", "", name)
                path = (
                    t.ROOT / "icones_aoe2"
                    / f"unidades_{safe}.json"
                )

                try:
                    document = json.loads(
                        path.read_text("utf-8")
                    )

                    for building in document["buildings"]:
                        self.buildings[
                            building["node_id"]
                        ] = building

                    nodes = document["units_techs"]
                    if isinstance(nodes, dict):
                        nodes = nodes.values()

                    for node in nodes:
                        if node.get("use_type") == "Tech":
                            self.tech[node["node_id"]] = node

                except Exception as exc:
                    self.errors.append(
                        "Metadados de pesquisa: " + str(exc)
                    )

        for record in self.records(session):
            ident = record["id"]
            node = self.tech.get(ident)

            if node:
                self.ensure(
                    "tech", ident,
                    node["picture_index"], "Tech",
                )

            producer = record["building"]
            building = self.buildings.get(producer)

            if building:
                self.ensure(
                    "building", producer,
                    building["picture_index"], "Building",
                )

    def ensure(self, kind, ident, picture, folder):
        key = kind, ident, picture
        if key in self.attempted:
            return
        self.attempted.add(key)

        filename = (
            f"building_{ident}.png"
            if kind == "building"
            else f"research_{ident}_{picture}.png"
        )
        path = t.ROOT / "icones_aoe2" / filename

        try:
            raw = path.read_bytes() if path.exists() else b""

            if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                with urllib.request.urlopen(
                    t.SOURCE + f"img/{folder}/{picture}.png",
                    timeout=15,
                ) as response:
                    raw = response.read(256 * 1024 + 1)

                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("PNG inválido.")

                t.atomic_write(path, raw)

            self.paths[(kind, ident)] = path

        except Exception as exc:
            self.errors.append(
                "Ícone de pesquisa: " + str(exc)
            )

    def records(self, session):
        result = []

        for event in session.research.values():
            if event.get("player") != 2:
                continue

            ident = event.get("technology_id")
            node = self.tech.get(ident, {})
            site = node.get("building_id")
            source = "tech_tree"

            for obj_id in event.get("object_ids", []):
                obj = session.objects.get(obj_id)
                if obj and obj["kind"] == "building":
                    site = obj["type_id"]
                    source = "initial_target"
                    break

            result.append({
                "id": ident,
                "name": event["name"],
                "building": site,
                "ms": event["ms"],
                "requests": event["requests"],
                "is_age": ident in (101, 102, 103),
                "association": source,
                "status": "research_requested_not_completed",
            })

        return sorted(
            result,
            key=lambda a: (a["ms"], a["id"]),
        )


RESEARCH = ResearchIcons()
_previous_frame = app.frame


def research_frame(session, *args, **kwargs):
    RESEARCH.prepare(session)
    return _previous_frame(session, *args, **kwargs)


app.frame = research_frame
_previous_state = p.order_state


def research_state(session):
    state = _previous_state(session)
    state["research_orders"] = RESEARCH.records(session)
    return state


p.order_state = research_state
_previous_report = p.state_report


def research_report(state):
    lines = [
        _previous_report(state),
        "",
        "J2 — ORDENS DE AVANÇO DE ERA E PESQUISA",
        "Ícones de pesquisa são pedidos identificados; "
        "não indicam conclusão nem progresso confirmado.",
        "Um edifício usado apenas como referência de pesquisa "
        "aparece sem contagem de construção.",
        "Paliçadas: linhas tracejadas representam pedidos; "
        "linhas sólidas vêm do estado inicial.",
        "Bolinhas indicam extremidades sem conexão identificável, "
        "não falhas comprovadas.",
        "Conexões usam recursos iniciais e footprints aproximados. "
        "Ausência de bolinhas não comprova fechamento.",
    ]

    for record in state.get("research_orders", []):
        name = p.BUILDING_CATALOG.get(
            record["building"],
            (f"Construção {record['building']}",),
        )[0]

        if record["building"] is None:
            name = "Construção não identificada"

        lines.append(
            f"{app.base.game_time(record['ms'])} | "
            f"{name} → {record['name']} | "
            f"{record['requests']} pedido(s)"
        )

    if RESEARCH.errors:
        lines.extend(RESEARCH.errors[-2:])

    return "\n".join(lines)


p.state_report = research_report
_previous_map = app.map_svg


def enhanced_map(session):
    import copy

    proxy = copy.copy(session)
    proxy.model = dict(session.model)
    proxy.model["points"] = [
        point for point in session.model["points"]
        if point["kind"] != "fazendas"
    ]
    proxy.initial = [
        obj for obj in session.initial
        if not (
            is_farm(session, obj["type_id"])
            or is_palisade(session, obj["type_id"])
        )
    ]
    proxy.build_requests = [
        event for event in session.build_requests
        if not (
            is_farm(session, event.get("building_id"))
            or is_palisade(
                session, event.get("building_id")
            )
        )
    ]

    root = ET.fromstring(_previous_map(proxy))
    layer = root.find(
        "{" + NS + '}g[@clip-path="url(#map-area)"]'
    )

    if layer is None:
        return ET.tostring(root, encoding="unicode")

    options = (
        t._projection_context.options
        or mini.SETTINGS[:2]
    )

    def point(x, y):
        return t._projection(
            x, y,
            session.model["dimension"],
            options[0], options[1],
        )

    def add(tag, **attrs):
        return ET.SubElement(
            layer,
            "{" + NS + "}" + tag,
            {k: str(v) for k, v in attrs.items()},
        )

    colors = {
        player["number"]: player["color_id"]
        for player in session.header.get("de", {}).get("players", [])
        if (
            player.get("number", -1) > 0
            and 0 <= player.get("color_id", -1) < 8
        )
    }

    edges, ends = wall_geometry(session)

    for first, second, planned in edges:
        owner, x, y = first

        start = (
            point(x + .5, y + .5)
            if second else point(x + .1, y + .5)
        )
        end = (
            point(second[1] + .5, second[2] + .5)
            if second else point(x + .9, y + .5)
        )

        fallback = (
            owner - 1
            if isinstance(owner, int) and owner > 0
            else 6
        )
        color = mini.PLAYER_COLORS[
            colors.get(owner, fallback) % 8
        ]

        attrs = {
            "x1": start[0],
            "y1": start[1],
            "x2": end[0],
            "y2": end[1],
            "stroke": color,
            "stroke-width": 2,
        }
        if planned:
            attrs["stroke-dasharray"] = "4 2"

        node = add("line", **attrs)
        ET.SubElement(node, "{" + NS + "}title").text = (
            "Traçado pedido; conclusão não confirmada."
            if planned
            else "Paliçada no estado inicial."
        )

    if VIEW[1]:
        for owner, x, y in ends:
            px, py = point(x + .5, y + .5)
            node = add(
                "circle",
                cx=px, cy=py, r=3.5,
                fill="none",
                stroke="#ffc65a",
                **{"stroke-width": 1.5},
            )
            ET.SubElement(node, "{" + NS + "}title").text = (
                "Possível abertura: sem conexão identificável "
                "nos dados disponíveis."
            )

    return ET.tostring(root, encoding="unicode")


app.map_svg = enhanced_map
mini.minimap_svg = enhanced_map


def research_rows(state, show_units=True, show_research=True):
    counts = dict(p.building_entries(state) or ())
    grouped = defaultdict(list)

    if show_research:
        for record in state.get("research_orders", []):
            grouped[record["building"]].append(record)

    ids = sorted(
        set(counts)
        | {
            ident for ident in grouped
            if isinstance(ident, int)
        }
    )

    rows = [
        (
            "building",
            ident,
            counts.get(ident),
            tuple(
                (record["id"], record["requests"])
                for record in grouped[ident]
            ),
        )
        for ident in ids
    ]

    if None in grouped:
        rows.append((
            "unknown",
            None,
            None,
            tuple(
                (record["id"], record["requests"])
                for record in grouped[None]
            ),
        ))

    if show_units:
        rows.extend(
            ("unit", int(ident), count, ())
            for ident, count in state.get(
                "military_orders", {}
            ).items()
            if count > 0
        )

    return rows


if hasattr(p, "CONFIG_DEFAULTS"):
    p.CONFIG_DEFAULTS.update(
        research_icons=True,
        wall_endpoints=True,
    )


class Window(t.Window):
    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)

        self.research_icons = tk.BooleanVar(value=True)
        self.wall_endpoints = tk.BooleanVar(value=True)

        box = ttk.LabelFrame(
            parent,
            text="Pesquisas e paliçadas",
            padding=8,
        )
        box.pack(
            fill="x", pady=6, before=self.report
        )

        ttk.Checkbutton(
            box,
            text="Pesquisas e avanços de era na barra",
            variable=self.research_icons,
        ).pack(anchor="w")

        ttk.Checkbutton(
            box,
            text=(
                "Marcar extremidades sem conexão identificável "
                "(possíveis aberturas)"
            ),
            variable=self.wall_endpoints,
        ).pack(anchor="w")

        ttk.Label(
            box,
            text=(
                "Bolinhas não confirmam falhas; sua ausência "
                "não comprova fechamento. Tecnologias são pedidos."
            ),
            wraplength=820,
        ).pack(anchor="w")

        for variable in (
            self.research_icons,
            self.wall_endpoints,
        ):
            variable.trace_add("write", self.view_options)

    def view_options(self, *args):
        global VIEW

        VIEW = (
            bool(self.research_icons.get()),
            bool(self.wall_endpoints.get()),
        )
        self.bar_cache = None
        self.next_frame = 0

    def __init__(self, root, native):
        super().__init__(root, native)
        self.view_options()
        root.title(
            "AoE2 — paliçadas, tropas e ordens de pesquisa de J2"
        )

    def picture(self, kind, ident, x, y, size):
        if not hasattr(self, "_research_photos"):
            self._research_photos = {}
            self._research_size = None

        if self._research_size != self._draw_size:
            self._research_photos.clear()
            self._research_size = self._draw_size

        key = kind, ident, int(size)

        if key not in self._research_photos:
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

            try:
                photo = tk.PhotoImage(
                    master=self.root,
                    file=str(path),
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
                x + size / 2,
                y + size / 2,
                image=photo,
            )
        else:
            self.canvas.create_text(
                x + size / 2,
                y + size / 2,
                text="?",
                fill="white",
                font=(
                    "Segoe UI",
                    max(8, int(size * .5)),
                ),
            )

    def draw_research_bar(self, rows, size):
        self._draw_size = size
        self.canvas.delete("all")

        pad = max(3, round(size * .12))
        row = round(size * 1.25)
        maxtech = max(
            (len(item[3]) for item in rows),
            default=0,
        )
        width = math.ceil(
            pad * 2 + size * 2.4 + maxtech * size * .65
        )

        for index, (kind, ident, count, techs) in enumerate(rows):
            y = pad + index * row
            self.picture(
                kind, ident, pad, y, size
            )

            if count is not None:
                self.canvas.create_text(
                    pad + size * 1.6,
                    y + size * .5,
                    text=f"{count}?",
                    fill="white",
                    font=(
                        "Segoe UI",
                        max(9, round(size * .45)),
                        "bold",
                    ),
                )

            for i, (tech, requests) in enumerate(techs):
                xx = pad + size * 2.4 + i * size * .65
                yy = y + size * .25

                self.picture(
                    "tech", tech,
                    xx, yy, size // 2,
                )
                self.canvas.create_text(
                    xx + size * .5,
                    yy + size * .5,
                    text=(
                        "?" if requests == 1
                        else f"{requests}?"
                    ),
                    fill="white",
                    anchor="se",
                    font=(
                        "Segoe UI",
                        max(6, round(size * .16)),
                        "bold",
                    ),
                )

        height = max(
            1, pad * 2 + row * len(rows)
        )
        self.canvas.configure(
            width=width, height=height
        )
        self.caption_size = width, height

    def tick(self):
        app.base.Window.tick(self)

        if self.closing:
            return

        rows = research_rows(
            self.bar_state,
            self.troops_bar.get(),
            self.research_icons.get(),
        )
        game = self.native.game()

        if not (
            rows
            and self.photo
            and self.caption_show.get()
            and (
                game
                or time.monotonic() < self.preview_until
            )
        ):
            self.caption.withdraw()
            return

        x, y, w, h = game or (
            0, 0,
            self.root.winfo_screenwidth(),
            self.root.winfo_screenheight(),
        )

        def number(variable, default, low, high):
            try:
                return min(
                    high, max(low, int(variable.get()))
                )
            except (ValueError, tk.TclError):
                return default

        maxtech = max(
            (len(item[3]) for item in rows),
            default=0,
        )
        size = min(
            number(self.bar_size, 48, 24, 120),
            max(
                2,
                int((h - 8) / (len(rows) * 1.25 + .3)),
            ),
            max(
                2,
                int((w - 8) / (2.7 + maxtech * .65)),
            ),
        )
        size = max(2, size - size % 2)

        cache = tuple(rows), size
        if cache != self.bar_cache:
            self.draw_research_bar(rows, size)
            self.bar_cache = cache

        self.caption.attributes(
            "-alpha", float(self.bar_opacity.get())
        )

        iw, ih = self.caption_size
        mx = number(self.caption_x, 20, 0, 10000)
        my = number(self.caption_y, 80, 0, 10000)
        corner = self.caption_corner.get()

        dx = (
            w - iw - mx
            if corner in (
                "Superior direito", "Inferior direito"
            )
            else mx
        )
        dy = (
            h - ih - my
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
            x + max(0, min(max(0, w - iw), dx)),
            y + max(0, min(max(0, h - ih), dy)),
            iw,
            ih,
            0x14,
        )
        self.caption.deiconify()


if __name__ == "__main__":
    native = app.base.Native()
    root = tk.Tk()
    Window(root, native)
    root.mainloop()