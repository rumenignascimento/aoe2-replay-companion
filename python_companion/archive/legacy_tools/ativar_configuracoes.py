"""Adiciona configurações persistentes ao painel_aoe2.py."""
import ast
from datetime import datetime
import os
from pathlib import Path
import shutil
import tempfile


SUPPORT = r'''
# CONFIGURACOES_PERSISTENTES_V1
CONFIG_DEFAULTS = {
    "folder": "",
    "width": 480,
    "opacity": 0.85,
    "show": True,
    "position_corner": "Superior direito",
    "position_x": 20,
    "position_y": 60,
    "map_turn": "0°",
    "map_mirror": False,
    "map_terrain": False,
    "caption_corner": "Superior esquerdo",
    "caption_x": 20,
    "caption_y": 80,
    "caption_show": True,
    "bar_size": 48,
    "bar_opacity": 1.0,
}


def _validate_config(values):
    if not isinstance(values, dict):
        raise ValueError("Formato de configurações inválido.")

    result = dict(CONFIG_DEFAULTS)

    ranges = {
        "width": (300, 900),
        "opacity": (.2, 1.0),
        "position_x": (0, 10000),
        "position_y": (0, 10000),
        "caption_x": (0, 10000),
        "caption_y": (0, 10000),
        "bar_size": (24, 120),
        "bar_opacity": (.2, 1.0),
    }
    corners = (
        "Superior esquerdo",
        "Superior direito",
        "Inferior esquerdo",
        "Inferior direito",
    )

    for key, default in CONFIG_DEFAULTS.items():
        if key not in values:
            continue

        value = values[key]

        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise ValueError(
                    f"{key}: use verdadeiro ou falso."
                )

        elif key in ranges:
            low, high = ranges[key]

            if isinstance(value, str):
                try:
                    value = float(value)
                except ValueError:
                    raise ValueError(
                        f"{key}: informe um número."
                    )

            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
            ):
                raise ValueError(
                    f"{key}: informe um número."
                )

            if not low <= value <= high:
                raise ValueError(
                    f"{key}: use um valor entre "
                    f"{low} e {high}."
                )

            if isinstance(default, int):
                if int(value) != value:
                    raise ValueError(
                        f"{key}: informe um número inteiro."
                    )
                value = int(value)

        elif key.endswith("corner"):
            if value not in corners:
                raise ValueError(f"{key}: canto inválido.")

        elif key == "map_turn":
            if value not in ("0°", "90°", "180°", "270°"):
                raise ValueError("Rotação inválida.")

        elif key == "folder":
            if (
                not isinstance(value, str)
                or len(value) > 4096
            ):
                raise ValueError(
                    "Caminho da pasta inválido."
                )

        result[key] = value

    return result


def _write_config(path, values):
    import json
    import os
    import tempfile
    from pathlib import Path

    path = Path(path)
    content = json.dumps(
        {
            "version": 1,
            "settings": _validate_config(values),
        },
        ensure_ascii=False,
        indent=2,
        allow_nan=False,
    )

    fd, temporary = tempfile.mkstemp(
        prefix=".config-",
        suffix=".tmp",
        dir=path.parent,
    )

    try:
        with os.fdopen(
            fd, "w", encoding="utf-8"
        ) as handle:
            handle.write(content)

        os.replace(temporary, path)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


'''


METHODS = r'''
    def setup_saved_settings(self):
        from pathlib import Path

        self.config_path = (
            Path(__file__).resolve()
            .with_name("configuracoes_aoe2.json")
        )

        panel = ttk.LabelFrame(
            self.report.master,
            text="Configurações",
            padding=8,
        )
        panel.pack(
            fill="x", pady=6, before=self.report
        )

        ttk.Button(
            panel,
            text="Salvar configurações",
            command=self.save_settings,
        ).pack(side="left", padx=4)

        ttk.Button(
            panel,
            text="Restaurar padrão",
            command=self.restore_settings,
        ).pack(side="left", padx=4)

        ttk.Label(
            panel,
            text="As configurações salvas são carregadas ao abrir.",
        ).pack(side="left", padx=10)

        self.load_settings()

    def apply_settings(self, values):
        from pathlib import Path

        values = _validate_config(values)
        folder = values["folder"]
        warning = ""

        try:
            if folder and not Path(folder).is_dir():
                warning = (
                    " A pasta savegame está indisponível; "
                    "selecione-a novamente."
                )
                folder = ""

            baseline = (
                set(Path(folder).glob("*.aoe2record"))
                if folder else set()
            )

        except OSError:
            warning = (
                " Não foi possível acessar a pasta savegame."
            )
            folder = ""
            baseline = set()

        for key, value in values.items():
            if key != "folder":
                getattr(self, key).set(value)

        self.folder.set(folder)
        self.baseline = baseline
        self.last_scan = 0

        self.alpha()
        self.map_options()
        self.caption.attributes(
            "-alpha", float(self.bar_opacity.get())
        )

        self.bar_cache = None
        self.next_frame = 0

        return warning

    def save_settings(self):
        from tkinter import messagebox

        try:
            values = {
                key: getattr(self, key).get()
                for key in CONFIG_DEFAULTS
            }
            _write_config(self.config_path, values)

        except Exception as exc:
            messagebox.showerror(
                "Não foi possível salvar",
                str(exc),
                parent=self.root,
            )
            return

        self.status.set(
            "Configurações salvas em "
            + str(self.config_path)
        )

    def load_settings(self):
        import json

        try:
            if not self.config_path.exists():
                return

            document = json.loads(
                self.config_path.read_text(
                    encoding="utf-8-sig"
                )
            )

            if (
                not isinstance(document, dict)
                or document.get("version") != 1
            ):
                raise ValueError(
                    "Formato de configuração não reconhecido."
                )

            warning = self.apply_settings(
                document.get("settings")
            )

        except Exception as exc:
            self.status.set(
                "Configuração não carregada; usando os padrões. "
                + str(exc)
            )
            return

        self.status.set(
            "Configurações carregadas." + warning
        )

    def restore_settings(self):
        from tkinter import messagebox

        try:
            _write_config(
                self.config_path, CONFIG_DEFAULTS
            )
            warning = self.apply_settings(
                CONFIG_DEFAULTS
            )

        except Exception as exc:
            messagebox.showerror(
                "Não foi possível restaurar",
                str(exc),
                parent=self.root,
            )
            return

        self.status.set(
            "Padrões originais restaurados e salvos."
            + warning
        )

'''


def install():
    target = (
        Path(__file__).resolve()
        .with_name("painel_aoe2.py")
    )

    if not target.is_file():
        raise RuntimeError(
            "Coloque este atualizador na mesma pasta "
            "de painel_aoe2.py."
        )

    source = target.read_text(
        encoding="utf-8-sig"
    )

    if "# CONFIGURACOES_PERSISTENTES_V1" in source:
        print(
            "A funcionalidade de configurações "
            "já está instalada."
        )
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

    if window is None or "bar_size" not in source:
        raise RuntimeError(
            "Este atualizador requer a versão "
            "com barra vertical de ícones."
        )

    init = next(
        node for node in window.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "__init__"
    )

    if any(
        isinstance(node, ast.FunctionDef)
        and node.name == "save_settings"
        for node in window.body
    ):
        raise RuntimeError(
            "Já existem métodos de configurações. "
            "Nenhum arquivo foi alterado."
        )

    lines = source.splitlines(keepends=True)

    insertions = [
        (
            window.end_lineno,
            "\n" + METHODS + "\n",
        ),
        (
            init.end_lineno,
            "\n        self.setup_saved_settings()\n",
        ),
        (
            window.lineno - 1,
            SUPPORT,
        ),
    ]

    for position, content in sorted(
        insertions, reverse=True
    ):
        lines.insert(position, content)

    updated = "".join(lines)

    # Confere a sintaxe antes de alterar o arquivo.
    compile(updated, str(target), "exec")

    backup = target.with_name(
        "painel_aoe2.backup_"
        + datetime.now().strftime("%Y%m%d_%H%M%S")
        + ".py"
    )
    shutil.copy2(target, backup)

    fd, temporary = tempfile.mkstemp(
        prefix=".painel-",
        suffix=".tmp",
        dir=target.parent,
    )

    try:
        with os.fdopen(
            fd, "w", encoding="utf-8"
        ) as handle:
            handle.write(updated)

        os.replace(temporary, target)

    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

    print("Atualização concluída.")
    print("Cópia anterior:", backup.name)
    print("Abra painel_aoe2.py normalmente.")


if __name__ == "__main__":
    try:
        install()
    except Exception as exc:
        print("Não foi possível atualizar:", exc)
        raise SystemExit(1)