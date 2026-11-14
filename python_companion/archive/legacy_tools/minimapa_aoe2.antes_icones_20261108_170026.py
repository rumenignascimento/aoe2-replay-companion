"""Minimapa com orientação ajustável e moldura discreta."""
import sys
import tkinter as tk
from tkinter import ttk
import xml.etree.ElementTree as ET

import overlay_legendas as app


NS = app.NS
KEY = app.KEY

# Rotação, espelhamento, exibição do terreno.
SETTINGS = (0, False, False)

PLAYER_COLORS = (
    "#0066ff", "#ff2020", "#00cc00", "#ffff00",
    "#00ffff", "#ff00aa", "#aaaaaa", "#ff8800",
)


def project(x, y, n, turns=0, mirror=False):
    for _ in range(turns % 4):
        x, y = n - y, x

    if mirror:
        x = n - x

    return (
        450 + (x - y) * 420 / n,
        15 + (x + y) * 210 / n,
    )


def minimap_svg(session):
    turns, mirror, terrain = SETTINGS
    n = session.model["dimension"]

    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": "900",
            "height": "450",
            "viewBox": "0 0 900 450",
            "shape-rendering": "crispEdges",
        },
    )

    def add(parent, tag, **attrs):
        return ET.SubElement(
            parent,
            "{" + NS + "}" + tag,
            {k: str(v) for k, v in attrs.items()},
        )

    def position(x, y):
        return project(x, y, n, turns, mirror)

    def polygon(parent, points, **attrs):
        return add(
            parent,
            "polygon",
            points=" ".join(
                f"{x:.3f},{y:.3f}" for x, y in points
            ),
            **attrs,
        )

    border = [
        (450, 15),
        (870, 225),
        (450, 435),
        (30, 225),
    ]

    add(
        root, "rect",
        width=900, height=450, fill=KEY,
    )

    defs = add(root, "defs")
    clip = add(defs, "clipPath", id="map-area")
    polygon(clip, border)

    layer = add(
        root, "g",
        **{"clip-path": "url(#map-area)"},
    )

    if terrain:
        palette = {
            0: "#8c9950",
            1: "#38759a",
            2: "#b5a46f",
            17: "#729047",
            27: "#ad9a65",
            89: "#849549",
            128: "#8c9950",
        }

        tiles = session.model["tiles"]

        for y in range(n):
            x = 0
            while x < n:
                terrain_id, height = tiles[y * n + x]
                end = x + 1

                while (
                    end < n
                    and tiles[y * n + end] == tiles[y * n + x]
                ):
                    end += 1

                polygon(
                    layer,
                    [
                        position(x, y),
                        position(end, y),
                        position(end, y + 1),
                        position(x, y + 1),
                    ],
                    fill=palette.get(terrain_id, "#8c9950"),
                )
                x = end

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

    def valid(x, y):
        return (
            isinstance(x, (int, float))
            and isinstance(y, (int, float))
            and 0 <= x < n
            and 0 <= y < n
        )

    def dot(x, y, size, color):
        px, py = position(x, y)
        add(
            layer,
            "rect",
            x=round(px - size / 2),
            y=round(py - size / 2),
            width=size,
            height=size,
            fill=color,
        )

    resources = {
        "madeira": "#006b00",
        "ouro": "#ffd600",
        "pedra": "#b8b8b8",
        "frutas": "#e00030",
        "caca": "#c09050",
        "rebanho": "#eeeecc",
        "peixes": "#38a8d8",
        "reliquias": "#ffffff",
    }

    for point in session.model["points"]:
        kind = point["kind"]

        if (
            kind not in resources
            or not valid(point["x"], point["y"])
        ):
            continue

        size = (
            max(2, round(420 / n * .65))
            if kind == "madeira"
            else 4
        )
        dot(
            point["x"], point["y"],
            size, resources[kind],
        )

    # Pedidos históricos continuam vazados.
    for event in list(session.build_requests)[-80:]:
        if not valid(event.get("x"), event.get("y")):
            continue

        x, y = position(event["x"], event["y"])
        node = add(
            layer,
            "rect",
            x=round(x - 4),
            y=round(y - 4),
            width=8,
            height=8,
            fill="none",
            stroke=owner_color(event.get("player")),
            **{
                "stroke-width": 1,
                "stroke-dasharray": "2 2",
            },
        )
        add(node, "title").text = (
            "Pedido histórico; conclusão não confirmada."
        )

    for obj in session.initial:
        if (
            obj["type_id"] in app.base.g.TC_IDS
            or not valid(obj["x"], obj["y"])
        ):
            continue

        dot(
            obj["x"],
            obj["y"],
            4 if obj["kind"] == "unit" else 7,
            owner_color(obj["owner"]),
        )

    # Centros urbanos e identificação dos jogadores.
    for point in session.model["points"]:
        if (
            point["kind"] != "centros"
            or not valid(point["x"], point["y"])
        ):
            continue

        owner = point["owner"]
        dot(
            point["x"], point["y"],
            11, owner_color(owner),
        )

        x, y = position(point["x"], point["y"])
        label = add(
            layer,
            "text",
            x=round(x + 8),
            y=round(y - 7),
            fill="white",
            **{
                "font-family": "Segoe UI, Arial",
                "font-size": 14,
                "font-weight": "bold",
            },
        )
        label.text = f"J{owner}"
        add(label, "title").text = (
            f"Centro urbano inicial do jogador {owner}."
        )

    # Moldura fina em tons discretos.
    polygon(
        root,
        border,
        fill="none",
        stroke="#493e2d",
        **{"stroke-width": 4},
    )
    polygon(
        root,
        border,
        fill="none",
        stroke="#a08c68",
        **{"stroke-width": 1},
    )

    return ET.tostring(root, encoding="unicode")


original_export = app.export_clean_png


def export_minimap(svg, png):
    tree = ET.parse(svg)
    root = tree.getroot()
    width = int(root.get("width"))
    root.set("height", str(max(1, round(width / 2))))
    tree.write(svg, encoding="unicode")
    original_export(svg, png)


OriginalWindow = app.Window


class MinimapWindow(OriginalWindow):
    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)

        self.map_turn = tk.StringVar(value="0°")
        self.map_mirror = tk.BooleanVar(value=False)
        self.map_terrain = tk.BooleanVar(value=False)

        panel = ttk.LabelFrame(
            parent,
            text="Orientação e aparência do minimapa",
            padding=8,
        )
        panel.pack(
            fill="x", pady=6, before=self.report
        )

        ttk.Label(
            panel, text="Rotação"
        ).grid(row=0, column=0, padx=4)

        ttk.Combobox(
            panel,
            textvariable=self.map_turn,
            values=("0°", "90°", "180°", "270°"),
            state="readonly",
            width=7,
        ).grid(row=0, column=1)

        ttk.Checkbutton(
            panel,
            text="Espelhar",
            variable=self.map_mirror,
        ).grid(row=0, column=2, padx=8)

        ttk.Checkbutton(
            panel,
            text="Mostrar terreno",
            variable=self.map_terrain,
        ).grid(row=0, column=3, padx=8)

        ttk.Label(
            panel,
            text=(
                "J1/J2 indicam centros urbanos iniciais. "
                "A moldura acompanha o mapa."
            ),
        ).grid(
            row=1,
            column=0,
            columnspan=4,
            sticky="w",
            pady=(5, 0),
        )

        for variable in (
            self.map_turn,
            self.map_mirror,
            self.map_terrain,
        ):
            variable.trace_add("write", self.map_options)

    def map_options(self, *args):
        global SETTINGS

        SETTINGS = (
            ("0°", "90°", "180°", "270°").index(
                self.map_turn.get()
            ),
            bool(self.map_mirror.get()),
            bool(self.map_terrain.get()),
        )
        self.next_frame = 0


app.map_svg = minimap_svg
app.export_clean_png = export_minimap
app.Window = MinimapWindow


if __name__ == "__main__":
    sys.modules["minimapa_aoe2"] = sys.modules[__name__]

    import painel_aoe2 as panel

    native = app.base.Native()
    root = tk.Tk()
    panel.Window(root, native)
    root.mainloop()