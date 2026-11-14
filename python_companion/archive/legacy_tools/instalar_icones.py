"""Instala ícones do AoE2 Tech Tree na barra existente."""
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

ASSETS = {
    "building": (
        "img/Building/7.png",
        "701d9fc3add461d23ed2bbe244172e1a5"
        "dec903bed113000c498435441dc80c9",
    ),
    "unit": (
        "img/Unit/15.png",
        "8d87e80dfe8fc639be662b6a5b80094b"
        "9ca46881fcda63416573a1c5a61d4b7c",
    ),
    "tech": (
        "img/Tech/6.png",
        "6a34d69d4c0735da73067b9bd47f7496"
        "9c524467dc51b45e72ca7938a0748a18",
    ),
}


METHOD = '''    # ICONES_AOE2_TECHTREE_V1
    def draw_icon(self, kind, x, y, size, color):
        from fractions import Fraction
        from pathlib import Path

        if kind not in ("building", "unit", "tech"):
            return self.draw_vector_icon(
                kind, x, y, size, color
            )

        if not hasattr(self, "_game_icon_originals"):
            self._game_icon_originals = {}
            self._game_icon_scaled = {}
            self._game_icon_size = None
            self._game_icon_failed = set()

        if kind in self._game_icon_failed:
            return self.draw_vector_icon(
                kind, x, y, size, color
            )

        try:
            if kind not in self._game_icon_originals:
                path = (
                    Path(__file__).resolve().parent
                    / "icones_aoe2"
                    / (kind + ".png")
                )
                self._game_icon_originals[kind] = (
                    tk.PhotoImage(
                        master=self.root,
                        file=str(path),
                    )
                )

            if self._game_icon_size != size:
                self._game_icon_scaled.clear()
                self._game_icon_size = size

            if kind not in self._game_icon_scaled:
                original = self._game_icon_originals[kind]

                ratio = Fraction(
                    max(1, round(size)),
                    max(original.width(), original.height()),
                ).limit_denominator(8)

                scaled = original.zoom(
                    ratio.numerator, ratio.numerator
                )

                if ratio.denominator != 1:
                    scaled = scaled.subsample(
                        ratio.denominator,
                        ratio.denominator,
                    )

                self._game_icon_scaled[kind] = scaled

            self.canvas.create_image(
                x + size / 2,
                y + size / 2,
                image=self._game_icon_scaled[kind],
                anchor="center",
            )

        except (OSError, tk.TclError) as exc:
            self._game_icon_failed.add(kind)
            self.status.set(
                "Ícone indisponível; execute "
                "instalar_icones.py novamente. "
                + str(exc)
            )
            self.draw_vector_icon(
                kind, x, y, size, color
            )

'''


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary = tempfile.mkstemp(
        prefix=".aoe2-",
        suffix=".tmp",
        dir=path.parent,
    )

    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)

        os.replace(temporary, path)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install():
    folder = Path(__file__).resolve().parent
    target = folder / "painel_aoe2.py"

    if not target.is_file():
        raise RuntimeError(
            "Coloque este instalador na mesma pasta "
            "de painel_aoe2.py."
        )

    source = target.read_text(encoding="utf-8-sig")
    tree = ast.parse(source)

    window = next(
        (
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "Window"
        ),
        None,
    )

    if window is None or "bar_size" not in source:
        raise RuntimeError(
            "É necessária a versão do painel "
            "com barra vertical de ícones."
        )

    installed = (
        "# ICONES_AOE2_TECHTREE_V1" in source
    )

    if not installed:
        method = next(
            (
                node for node in window.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "draw_icon"
            ),
            None,
        )

        if method is None:
            raise RuntimeError(
                "Método draw_icon não encontrado. "
                "Nenhum código foi alterado."
            )

        if any(
            isinstance(node, ast.FunctionDef)
            and node.name == "draw_vector_icon"
            for node in window.body
        ):
            raise RuntimeError(
                "Já existe um método draw_vector_icon. "
                "Nenhum código foi alterado."
            )

        lines = source.splitlines(keepends=True)
        index = method.lineno - 1

        lines[index] = lines[index].replace(
            "def draw_icon(",
            "def draw_vector_icon(",
            1,
        )
        lines.insert(index, METHOD)

        updated = "".join(lines)
        compile(updated, str(target), "exec")

    assets = folder / "icones_aoe2"
    manifest = {}

    for kind, (remote, digest) in ASSETS.items():
        path = assets / (kind + ".png")
        data = (
            path.read_bytes()
            if path.is_file() else b""
        )

        if hashlib.sha256(data).hexdigest() != digest:
            print("Baixando:", remote)

            request = urllib.request.Request(
                SOURCE + remote,
                headers={
                    "User-Agent": "AoE2-Local-Icons/1.0"
                },
            )

            with urllib.request.urlopen(
                request, timeout=30
            ) as response:
                data = response.read(256 * 1024 + 1)

            if (
                not data.startswith(b"\x89PNG\r\n\x1a\n")
                or hashlib.sha256(data).hexdigest() != digest
            ):
                raise RuntimeError(
                    "A imagem não passou na verificação: "
                    + remote
                )

            atomic_write(path, data)

        manifest[kind] = {
            "source": SOURCE + remote,
            "sha256": digest,
        }

    credits = (
        "Ícones obtidos de "
        "https://github.com/SiegeEngineers/aoe2techtree\n"
        "Castelo (Building/7), aldeão (Unit/15), "
        "Tear (Tech/6).\n"
        "Age of Empires II © Microsoft Corporation.\n"
        "Game Icons © Hidden Path Entertainment, "
        "Forgotten Empires, SkyBox Labs, Ensemble Studios.\n"
        "Projeto AoE2 Tech Tree: Siege Engineers / "
        "HSZemi e colaboradores.\n"
        "https://www.xbox.com/en-us/developers/rules\n"
    )

    atomic_write(
        assets / "CREDITOS.txt",
        credits.encode("utf-8"),
    )
    atomic_write(
        assets / "origem.json",
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8"),
    )

    if not installed:
        backup = target.with_name(
            "painel_aoe2.antes_icones_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".py"
        )

        shutil.copy2(target, backup)
        atomic_write(
            target, updated.encode("utf-8")
        )
        print("Backup:", backup.name)

    print(
        "Ícones instalados. "
        "Abra painel_aoe2.py normalmente."
    )


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print(
            "Não foi possível instalar os ícones:",
            exc,
        )
        raise SystemExit(1)