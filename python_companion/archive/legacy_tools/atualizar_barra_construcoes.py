"""Barra por tipo de construção confirmada do jogador 2."""
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
    (12, "Quartel", 2,
     "4198a60591b17fda07b48b57cbad43e6620e3618867882138d1fed39774352b0"),
    (45, "Porto", 13,
     "17ba0932215f01f44ec42f1a7bb9964d742c11e9c3ba6de3bb38e3527532d4e9"),
    (49, "Oficina de cerco", 22,
     "a63ed7edbc550b7916fe2213c7e7b890ba704a0c3624f7e207b7d9c461746f65"),
    (68, "Moinho", 19,
     "56578ebb5a4f4ae6de215fe0b2b7185d596be20a64995c069a336f50d718a411"),
    (82, "Castelo", 7,
     "701d9fc3add461d23ed2bbe244172e1a5dec903bed113000c498435441dc80c9"),
    (84, "Mercado", 16,
     "efd5891419d4faefb62556dd70e31884dd3457bba26a4eb89aec123588d92671"),
    (87, "Campo de arqueiros", 0,
     "481171f30ac2314bce39b9ebc3c020339e2452a1b091df03546e024d34a7b257"),
    (101, "Estábulo", 23,
     "547b2cf7771cdda392ef1fe9724f0ebc4fafa2669fb755a59681f61e2a23860c"),
    (103, "Ferraria", 4,
     "a4b7228e1e6ad9fee113a304e6edf761b7b5bf9993e86cc0f2b5ccf1246aedf9"),
    (104, "Mosteiro", 10,
     "18c4b8e689b93be80e9c4002fb1c9bc08238dbdba90b755b2a04d4926290caf9"),
    (109, "Centro urbano", 28,
     "5c8e27c91b9b4950f3adf9cefbdacae56378a982a7d5eec1c65d8763ad88e7d2"),
    (209, "Universidade", 33,
     "fefd3e8029471cfe39f3b509771278fdeb2f56cd2927124940196e3424f732cd"),
    (562, "Acampamento madeireiro", 40,
     "074c3a229b4e96f38aec5c86ff26ff93217c2b62b50954a06d66e6ab817a905b"),
    (584, "Acampamento de mineração", 39,
     "71f4f0c451a8d9428b3ad070667919560815aa80435b65e931ca393e42a4f559"),
    (1251, "Krepost", 55,
     "16147710606ff362e40d4ba292b1e7fc15f2d85f5df5933e919e54241c4044db"),
    (1665, "Donjon", 84,
     "28d3d10bac386ba1ad535fb1ae774ab800b9201077450a85f4f1e7dc1bdbd1b2"),
    (1734, "Folwark", 86,
     "538d52ae4c065a8d8790c1ca846d92388ceb7d96d5f8659c389f48fb48888139"),
    (1806, "Igreja fortificada", 88,
     "79b181b60d7d75cc8d10b584a6d4add129742d0114c37eca19e2461fe782ef1e"),
    (1808, "Carro de mulas", 89,
     "8b51b0d02a4086af34e9f641964f00c5d28073b1ae9f6bdcbdab87aa9a1d51e7"),
    (2556, "Assentamento", 98,
     "16319412f5414f66ab47b4bc4884d73dfc69d2a283efe924c1651fbcb0bb78aa"),
]


MODEL = r'''
BUILDING_CATALOG = __CATALOG__


def confirmed_state(session):
    # A fonte atual não fornece contagens de conclusões.
    # Não converter ordens de construção em edifícios prontos.
    return {
        "player": 2,
        "game_ms": session.ms,
        "building_counts": None,
        "source": "replay_orders_only",
    }


def building_entries(state):
    if state.get("player") != 2:
        return None

    counts = state.get("building_counts")
    if not isinstance(counts, dict):
        return None

    result = {}

    for raw_id, count in counts.items():
        if isinstance(raw_id, bool):
            return None
        if not isinstance(raw_id, (int, str)):
            return None

        try:
            ident = int(raw_id)
        except (ValueError, TypeError):
            return None

        if (
            not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            return None

        if ident in result:
            return None

        if ident in BUILDING_CATALOG and count > 0:
            result[ident] = count

    return tuple(sorted(result.items()))


def state_report(state):
    entries = building_entries(state)
    lines = [
        "JOGADOR 2 — CONSTRUÇÕES CONCLUÍDAS CONFIRMADAS",
        f"Registros até {app.base.game_time(state['game_ms'])}",
        "",
    ]

    if entries is None:
        lines.extend([
            "Contagens de conclusões indisponíveis na fonte atual.",
            "A barra fica oculta enquanto não houver dados confirmados.",
            "Isso não significa que o jogador tenha zero construções.",
            "Pedidos não serão exibidos como edifícios prontos.",
        ])
    elif not entries:
        lines.append(
            "Nenhuma construção elegível confirmada "
            "com quantidade maior que zero."
        )
    else:
        lines.extend(
            f"{BUILDING_CATALOG[ident][0]}: {count}"
            for ident, count in entries
        )

    return "\n".join(lines)

'''


METHODS = r'''
    def setup_building_bar(self):
        self.root.title(
            "AoE2 — construções concluídas confirmadas de J2"
        )

        for panel in self.report.master.winfo_children():
            if (
                isinstance(panel, ttk.LabelFrame)
                and str(panel.cget("text")).startswith(
                    "Barra vertical"
                )
            ):
                for label in panel.winfo_children():
                    if (
                        isinstance(label, ttk.Label)
                        and "ampulheta" in str(label.cget("text"))
                    ):
                        label.configure(
                            text=(
                                "Um ícone por construção; "
                                "número = quantidade confirmada. "
                                "Sem dados, a barra fica oculta."
                            )
                        )

    def draw_building_icon(self, ident, x, y, size):
        from fractions import Fraction
        from pathlib import Path

        if not hasattr(self, "_building_originals"):
            self._building_originals = {}
            self._building_scaled = {}
            self._building_size = None

        if self._building_size != size:
            self._building_scaled.clear()
            self._building_size = size

        try:
            if ident not in self._building_originals:
                path = (
                    Path(__file__).resolve().parent
                    / "icones_aoe2"
                    / f"building_{ident}.png"
                )
                self._building_originals[ident] = tk.PhotoImage(
                    master=self.root,
                    file=str(path),
                )

            if ident not in self._building_scaled:
                image = self._building_originals[ident]
                ratio = Fraction(
                    max(1, round(size)),
                    max(image.width(), image.height()),
                ).limit_denominator(8)

                image = image.zoom(
                    ratio.numerator, ratio.numerator
                )
                if ratio.denominator != 1:
                    image = image.subsample(
                        ratio.denominator, ratio.denominator
                    )

                self._building_scaled[ident] = image

            self.canvas.create_image(
                x + size / 2,
                y + size / 2,
                image=self._building_scaled[ident],
                anchor="center",
            )

        except (OSError, tk.TclError) as exc:
            self.canvas.create_text(
                x + size / 2,
                y + size / 2,
                text="?",
                fill="white",
                font=("Segoe UI", max(10, round(size * .5))),
            )
            self.status.set(
                "Ícone indisponível: "
                + BUILDING_CATALOG[ident][0]
                + ". "
                + str(exc)
            )

    def draw_bar(self, size):
        entries = building_entries(self.bar_state) or ()
        self.canvas.delete("all")

        pad = max(3, round(size * .12))
        row = max(1, round(size * 1.25))
        width = round(size * 2.1) + pad * 2

        for index, (ident, count) in enumerate(entries):
            y = pad + index * row
            self.draw_building_icon(
                ident, pad, y, size
            )
            self.canvas.create_text(
                pad + size * 1.55,
                y + size * .5,
                text=str(count),
                fill="white",
                font=(
                    "Segoe UI",
                    max(9, round(size * .48)),
                    "bold",
                ),
            )

        height = max(
            1, pad * 2 + row * len(entries)
        )
        self.canvas.configure(
            width=width, height=height
        )
        self.caption_size = width, height

    def tick(self):
        app.base.Window.tick(self)

        if self.closing:
            return

        entries = building_entries(self.bar_state)
        game = self.native.game()

        if not (
            entries
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

        size = number(
            self.bar_size, 48, 24, 120
        )
        size = min(
            size,
            max(1, int((h - 8) / (len(entries) * 1.25 + .3))),
            max(1, int((w - 8) / 2.4)),
        )

        cache = entries, size
        if cache != self.bar_cache:
            self.draw_bar(size)
            self.bar_cache = cache

        try:
            self.caption.attributes(
                "-alpha", float(self.bar_opacity.get())
            )
        except (ValueError, tk.TclError):
            pass

        iw, ih = self.caption_size
        mx = number(self.caption_x, 20, 0, 10000)
        my = number(self.caption_y, 80, 0, 10000)
        corner = self.caption_corner.get()

        dx = (
            w - iw - mx
            if corner in ("Superior direito", "Inferior direito")
            else mx
        )
        dy = (
            h - ih - my
            if corner in ("Inferior esquerdo", "Inferior direito")
            else my
        )

        ox = x + max(0, min(max(0, w - iw), dx))
        oy = y + max(0, min(max(0, h - ih), dy))

        self.caption.geometry(f"{iw}x{ih}")
        self.caption.update_idletasks()
        self.native.u.SetWindowPos(
            self.caption_hwnd, None,
            ox, oy, iw, ih, 0x14,
        )
        self.caption.deiconify()

'''


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, name = tempfile.mkstemp(
        prefix=".aoe2-",
        suffix=".tmp",
        dir=path.parent,
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def install():
    folder = Path(__file__).resolve().parent
    target = folder / "painel_aoe2.py"

    if not target.exists():
        raise RuntimeError(
            "Coloque o atualizador na pasta de painel_aoe2.py."
        )

    source = target.read_text(encoding="utf-8-sig")

    if "# BARRA_CONSTRUCOES_CONFIRMADAS_V1" in source:
        print("Esta atualização já está instalada.")
        return

    tree = ast.parse(source)
    window = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == "Window"
    )

    old = {
        node.name: node
        for node in window.body
        if isinstance(node, ast.FunctionDef)
    }

    if (
        not {"__init__", "draw_bar", "tick"} <= old.keys()
        or "bar_size" not in source
    ):
        raise RuntimeError(
            "O painel precisa estar na versão da barra vertical."
        )

    lines = source.splitlines(keepends=True)
    edits = []

    for node in tree.body:
        if (
            isinstance(node, ast.FunctionDef)
            and node.name in ("confirmed_state", "state_report")
        ):
            edits.append((
                node.lineno - 1,
                node.end_lineno,
                "",
            ))

    for name in ("draw_bar", "tick"):
        node = old[name]
        edits.append((
            node.lineno - 1,
            node.end_lineno,
            "",
        ))

    names = {
        ident: (name, f"building_{ident}.png")
        for ident, name, picture, digest in ASSETS
    }

    support = (
        "# BARRA_CONSTRUCOES_CONFIRMADAS_V1\n"
        + MODEL.replace("__CATALOG__", repr(names))
    )

    edits.extend([
        (
            window.lineno - 1,
            window.lineno - 1,
            support,
        ),
        (
            window.end_lineno,
            window.end_lineno,
            "\n" + METHODS + "\n",
        ),
        (
            old["__init__"].end_lineno,
            old["__init__"].end_lineno,
            "\n        self.setup_building_bar()\n",
        ),
    ])

    for start, end, content in sorted(edits, reverse=True):
        lines[start:end] = [content]

    updated = "".join(lines)
    compile(updated, str(target), "exec")

    assets = folder / "icones_aoe2"
    manifest = {}

    for ident, name, picture, digest in ASSETS:
        path = assets / f"building_{ident}.png"
        data = path.read_bytes() if path.exists() else b""
        remote = SOURCE + f"img/Building/{picture}.png"

        if hashlib.sha256(data).hexdigest() != digest:
            print("Baixando:", name)

            with urllib.request.urlopen(
                remote, timeout=30
            ) as response:
                data = response.read(256 * 1024 + 1)

            if (
                not data.startswith(b"\x89PNG\r\n\x1a\n")
                or hashlib.sha256(data).hexdigest() != digest
            ):
                raise RuntimeError(
                    "Ícone inválido: " + name
                )

            atomic_write(path, data)

        manifest[str(ident)] = {
            "name": name,
            "url": remote,
            "sha256": digest,
        }

    atomic_write(
        assets / "construcoes.json",
        json.dumps(
            manifest, ensure_ascii=False, indent=2
        ).encode("utf-8"),
    )

    atomic_write(
        assets / "CREDITOS_CONSTRUCOES.txt",
        (
            "Fonte: SiegeEngineers/aoe2techtree\n"
            "Age of Empires II © Microsoft Corporation.\n"
            "Game Icons © Hidden Path Entertainment, "
            "Forgotten Empires, SkyBox Labs, Ensemble Studios.\n"
            "https://github.com/SiegeEngineers/aoe2techtree\n"
        ).encode("utf-8"),
    )

    backup = target.with_name(
        "painel_aoe2.antes_construcoes_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".py"
    )
    shutil.copy2(target, backup)
    atomic_write(target, updated.encode("utf-8"))

    print("Atualização concluída. Backup:", backup.name)
    print(
        "Sem contagens confirmadas, a barra ficará oculta. "
        "Pedidos não serão contados."
    )


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print("Não foi possível atualizar:", exc)
        raise SystemExit(1)