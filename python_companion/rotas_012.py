import copy
import struct
import xml.etree.ElementTree as ET
from collections import defaultdict


def ativar(g):
    if g.get("_rotas_012_ativas"):
        return
    g["_rotas_012_ativas"] = True

    Base = g["AllSession"]
    t, mini = g["t"], g["mini"]

    class Session(Base):
        def __init__(self, path):
            super().__init__(path)
            self.route_selection = {}
            self.routes = {}
            self.route_decoded = 0
            self.route_reused = 0
            self.route_appended = 0
            self.route_missing = 0

        def poll(self, *args, **kwargs):
            with t.AI_PARSE_LOCK:
                original = self.fast.parse_action

                def decode(action, raw):
                    payload = original(action, raw)

                    # Layout validado com os replays deste projeto.
                    if (
                        action.name == "MOVE"
                        and self.model.get("build") == 188329
                        and len(raw) >= 23
                    ):
                        selected = struct.unpack_from(
                            "<h", raw, 15
                        )[0]

                        valid = (
                            len(raw)
                            == struct.unpack_from("<h", raw, 1)[0] + 3
                            and raw[17] == 0
                            and raw[18] in (0, 1)
                            and raw[19:23] == b"\x01\x01\x00\x00"
                            and (
                                selected == -1 and len(raw) == 23
                                or selected > 0
                                and len(raw) == 23 + 4 * selected
                            )
                        )

                        if valid:
                            payload["_route_append"] = bool(raw[18])
                            payload["_route_reuse"] = selected == -1

                    return payload

                self.fast.parse_action = decode
                try:
                    return super().poll(*args, **kwargs)
                finally:
                    self.fast.parse_action = original

        def apply(self, action, payload):
            if not hasattr(self, "routes"):
                return super().apply(action, payload)

            payload = dict(payload)
            owner = payload.get("player_id")
            ids = list(dict.fromkeys(
                payload.get("object_ids", [])
            ))
            valid = (
                action == "MOVE"
                and "_route_append" in payload
            )

            if valid and owner in self.all_players:
                if payload.get("_route_reuse"):
                    ids = list(
                        self.route_selection.get(owner, [])
                    )
                    payload["object_ids"] = ids
                    self.route_reused += bool(ids)
                    self.route_missing += not bool(ids)
                elif ids:
                    self.route_selection[owner] = list(ids)

            super().apply(action, payload)

            if not valid:
                if action in (
                    "STOP", "DELETE", "MOVE", "ORDER",
                    "PATROL", "DE_ATTACK_MOVE", "AI_ORDER",
                ):
                    for ident in ids:
                        self.routes.pop(ident, None)
                return

            x, y = payload.get("x"), payload.get("y")
            if (
                owner not in self.all_players
                or not self.valid_destination(x, y)
            ):
                return

            self.route_decoded += 1
            self.route_appended += bool(
                payload["_route_append"]
            )

            for ident in ids:
                obj = self.all_objects.get(ident)

                if obj and (
                    obj["kind"] != "unit"
                    or obj["type_id"] in t.CIVILIAN_IDS
                    or str(obj["name"]).casefold()
                    in t.CIVILIAN_NAMES
                ):
                    continue

                old = self.routes.get(ident)
                append = (
                    payload["_route_append"]
                    and old is not None
                )

                if append:
                    origin = old["origin"]
                elif old:
                    origin = (
                        *old["points"][-1],
                        "previous_target",
                    )
                elif obj:
                    origin = (
                        obj["x"], obj["y"], "initial"
                    )
                else:
                    origin = None

                points = list(old["points"]) if append else []
                points.append((x, y))

                self.routes[ident] = dict(
                    player=owner,
                    ms=self.ms,
                    type_id=obj["type_id"] if obj else None,
                    name=(
                        obj["name"]
                        if obj else "Tipo desconhecido"
                    ),
                    origin=origin,
                    points=points,
                )

        def all_movements(
            self, players, horizon=60000, limit=3
        ):
            grouped = {}

            for ident, route in self.routes.items():
                if (
                    route["player"] not in players
                    or route["ms"] < self.ms - horizon
                ):
                    continue

                key = (
                    route["player"],
                    tuple(route["points"]),
                )
                event = grouped.setdefault(
                    key,
                    dict(
                        player=route["player"],
                        ms=route["ms"],
                        destination=list(route["points"][-1]),
                        action="MOVE",
                        groups={},
                    ),
                )
                event["ms"] = max(event["ms"], route["ms"])

                group = event["groups"].setdefault(
                    route["type_id"],
                    dict(
                        type_id=route["type_id"],
                        name=route["name"],
                        count=0,
                        origins=[],
                        route_points=[
                            list(p) for p in route["points"]
                        ],
                    ),
                )

                group["count"] += 1
                if route["origin"]:
                    group["origins"].append(route["origin"])

            result = []
            counts = defaultdict(int)

            for event in sorted(
                grouped.values(),
                key=lambda e: e["ms"],
                reverse=True,
            ):
                if counts[event["player"]] >= limit:
                    continue

                counts[event["player"]] += 1
                event["groups"] = list(
                    event["groups"].values()
                )

                for group in event["groups"]:
                    origins = group.pop("origins")
                    group["origin_count"] = len(origins)
                    group["origin"] = (
                        [
                            sum(p[i] for p in origins)
                            / len(origins)
                            for i in (0, 1)
                        ]
                        if origins else None
                    )
                    group["origin_sources"] = sorted({
                        p[2] for p in origins
                    })

                result.append(event)

            # Mantém o leitor anterior para outros comandos.
            shadow = copy.copy(self)
            shadow.all_latest = dict(self.all_latest)

            for ident in self.routes:
                shadow.all_latest[ident] = -1

            for event in Base.all_movements(
                shadow, players, horizon, limit
            ):
                if counts[event["player"]] < limit:
                    result.append(event)
                    counts[event["player"]] += 1

            return result

    g["AllSession"] = Session
    g["p"].OrderSession = Session
    old_map = g["selected_map"]

    def draw(session):
        wanted = g["selected_ids"](session)
        events = session.all_movements(
            wanted, t.OPTIONS[2] * 1000, 3
        )

        shadow = copy.copy(session)
        clean = copy.deepcopy(events)

        # O desenho antigo mantém os ícones e quantitativos.
        # Os segmentos são desenhados abaixo.
        for event in clean:
            for group in event["groups"]:
                if "route_points" in group:
                    group["origin"] = None

        shadow.all_movements = lambda *a, **k: clean
        root = ET.fromstring(old_map(shadow))
        ns = g["NS"]

        layer = root.find(
            "{" + ns + '}g[@clip-path="url(#map-area)"]'
        )

        if layer is None or not t.OPTIONS[0]:
            return ET.tostring(root, encoding="unicode")

        options = (
            t._projection_context.options
            or mini.SETTINGS[:2]
        )

        colors = {
            a["number"]: a["color_id"]
            for a in session.header.get(
                "de", {}
            ).get("players", [])
            if a.get("number", -1) > 0
            and 0 <= a.get("color_id", -1) < 8
        }

        def point(p):
            return t._projection(
                p[0], p[1],
                session.model["dimension"],
                options[0], options[1],
            )

        for event in events:
            owner = event["player"]
            color = mini.PLAYER_COLORS[
                colors.get(owner, (owner - 1) % 8)
            ]
            drawn = set()

            for group in event["groups"]:
                points = group.get("route_points")
                if not points:
                    continue

                origin = group["origin"]
                key = (
                    tuple(map(tuple, points)),
                    tuple(origin) if origin else None,
                )
                if key in drawn:
                    continue
                drawn.add(key)

                path = (
                    ([origin] if origin else [])
                    + points
                )

                node = ET.SubElement(
                    layer,
                    "{" + ns + "}polyline",
                    {
                        "points": " ".join(
                            f"{x},{y}"
                            for x, y in map(point, path)
                        ),
                        "fill": "none",
                        "stroke": color,
                        "stroke-width": "1.5",
                        "stroke-dasharray": "4 3",
                        "marker-end": (
                            f"url(#all-arrow-{owner})"
                        ),
                    },
                )
                ET.SubElement(
                    node, "{" + ns + "}title"
                ).text = (
                    "Destinos solicitados; percurso e "
                    "posição atuais não confirmados."
                )

                for index, p in enumerate(points, 1):
                    x, y = point(p)

                    ET.SubElement(
                        layer,
                        "{" + ns + "}circle",
                        {
                            "cx": str(x),
                            "cy": str(y),
                            "r": "3",
                            "fill": color,
                        },
                    )
                    ET.SubElement(
                        layer,
                        "{" + ns + "}text",
                        {
                            "x": str(x + 4),
                            "y": str(y - 4),
                            "fill": color,
                            "font-size": "10",
                        },
                    ).text = str(index)

        return ET.tostring(root, encoding="unicode")

    g["selected_map"] = draw
    g["app"].map_svg = draw
    mini.minimap_svg = draw
