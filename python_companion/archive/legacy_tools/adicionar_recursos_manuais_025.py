import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r"""
import copy
import json
import os
from pathlib import Path
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from central_replay import BG, CARD, TEXT, EDGE, BRONZE


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.error = None
        self.matches = {}

        try:
            if self.path.exists():
                data = json.loads(
                    self.path.read_text("utf-8")
                )
                if (
                    not isinstance(data, dict)
                    or data.get("version") != 1
                    or not isinstance(data.get("matches"), dict)
                ):
                    raise ValueError("Formato inválido")

                self.matches = data["matches"]

                for entry in self.matches.values():
                    if (
                        not isinstance(entry, dict)
                        or not isinstance(entry.get("hidden"), list)
                        or not isinstance(entry.get("history"), list)
                    ):
                        raise ValueError("Registro inválido")

                    if any(
                        not isinstance(item, int)
                        for item in entry["hidden"]
                    ) or any(
                        not isinstance(values, list)
                        or any(
                            not isinstance(item, int)
                            for item in values
                        )
                        for values in entry["history"]
                    ):
                        raise ValueError("IDs inválidos")

        except (OSError, ValueError, TypeError) as error:
            self.error = str(error)
            self.matches = {}

    def hidden(self, digest):
        with self.lock:
            return set(
                self.matches.get(digest, {}).get("hidden", [])
            )

    def save(self):
        self.path.parent.mkdir(
            parents=True, exist_ok=True
        )
        fd, temporary = tempfile.mkstemp(
            prefix="recursos-",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(
                    dict(version=1, matches=self.matches),
                    handle,
                    ensure_ascii=False,
                )
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def change(
        self, digest, ids=None, undo=False, restore=False
    ):
        with self.lock:
            if self.error:
                raise ValueError(
                    "Não foi possível ler as anotações existentes: "
                    + self.error
                )

            previous = copy.deepcopy(
                self.matches.get(digest)
            )
            entry = self.matches.setdefault(
                digest, dict(hidden=[], history=[])
            )

            if undo:
                if not entry["history"]:
                    return False
                entry["hidden"] = entry["history"].pop()
            else:
                hidden = set(entry["hidden"])
                new = (
                    set() if restore
                    else hidden | set(ids or [])
                )
                if hidden == new:
                    return False

                entry["history"].append(sorted(hidden))
                entry["history"] = entry["history"][-100:]
                entry["hidden"] = sorted(new)

            try:
                self.save()
            except Exception:
                if previous is None:
                    self.matches.pop(digest, None)
                else:
                    self.matches[digest] = previous
                raise

            return True


def ativar(g):
    if g.get("_recursos_manuais_ativos"):
        return
    g["_recursos_manuais_ativos"] = True

    app = g["app"]
    store = Store(
        app.base.ROOT / "recursos_marcados.json"
    )
    g["RESOURCE_STORE"] = store

    kinds = {
        "madeira", "ouro", "pedra", "frutas",
        "caca", "rebanho", "peixes",
    }
    names = {
        "madeira": "Árvore / madeira",
        "ouro": "Ouro",
        "pedra": "Pedra",
        "frutas": "Frutas",
        "caca": "Caça",
        "rebanho": "Animal de rebanho",
        "peixes": "Peixe",
    }

    def objects(session):
        result = {}

        for obj in session.model["points"]:
            if obj["kind"] in kinds:
                result[obj["instance"]] = dict(
                    id=obj["instance"],
                    name=names[obj["kind"]],
                    x=obj["x"],
                    y=obj["y"],
                )

        for obj in g["gaia_records"](session):
            result.setdefault(
                obj["id"],
                dict(
                    id=obj["id"],
                    name="Gaia: " + obj["name"],
                    x=obj["x"],
                    y=obj["y"],
                ),
            )

        return list(result.values())

    old_render = app.map_svg

    def render(session):
        hidden = store.hidden(session.digest)
        view = copy.copy(session)
        view.model = dict(session.model)

        view.model["points"] = [
            point for point in session.model["points"]
            if point.get("instance") not in hidden
        ]
        view.initial = [
            point for point in session.initial
            if point["id"] not in hidden
        ]

        view.header = dict(session.header)
        view.header["players"] = []

        for player in session.header["players"]:
            item = dict(player)
            item["objects"] = [
                obj for obj in player["objects"]
                if obj["instance_id"] not in hidden
            ]
            view.header["players"].append(item)

        view._full_session = view
        return old_render(view)

    app.map_svg = render
    g["mini"].minimap_svg = render
    g["selected_map"] = render

    old_frame = app.frame

    def frame(session, *args, **kwargs):
        data = old_frame(session, *args, **kwargs)

        options = (
            g["t"]._projection_context.options
            or g["mini"].SETTINGS[:2]
        )
        hidden = store.hidden(session.digest)
        points = []

        for obj in objects(session):
            if obj["id"] in hidden:
                continue

            point = dict(obj)
            point["px"], point["py"] = g["t"]._projection(
                obj["x"], obj["y"],
                session.model["dimension"],
                options[0], options[1],
            )
            points.append(point)

        data["resource_view"] = dict(
            digest=session.digest,
            points=points,
        )
        return data

    app.frame = frame
    Base = g["Window"]

    class Queue:
        def __init__(self, inner, window):
            self.inner = inner
            self.window = window

        def __getattr__(self, key):
            return getattr(self.inner, key)

        def get_nowait(self):
            result = self.inner.get_nowait()
            epoch, kind, session, data = result

            if epoch == self.window.epoch and kind == "ok":
                self.window.resource_view = data.get(
                    "resource_view"
                )

            return result

    class Window(Base):
        def __init__(self, *args, **kwargs):
            self.resource_view = None
            self.resource_mode = False
            super().__init__(*args, **kwargs)
            self.queue = Queue(self.queue, self)

        def attach(self, *args, **kwargs):
            self.resource_view = None
            return super().attach(*args, **kwargs)

        def resource_controls(self):
            box = ttk.Frame(
                self.overview,
                style="Card.TFrame",
                padding=8,
            )
            box.pack(fill="x", pady=(8, 0))

            row = ttk.Frame(
                box, style="Card.TFrame"
            )
            row.pack(fill="x")

            self.resource_button = ttk.Button(
                row,
                text="Marcar recurso esgotado",
                command=self.toggle_resource_mode,
            )
            self.resource_button.pack(side="left")

            ttk.Button(
                row,
                text="Desfazer",
                command=lambda: self.resource_action(
                    undo=True
                ),
            ).pack(side="left", padx=6)

            ttk.Button(
                row,
                text="Restaurar marcadores",
                command=lambda: self.resource_action(
                    restore=True
                ),
            ).pack(side="left")

            self.resource_note = tk.StringVar(
                value=(
                    "Marcação manual: ative o modo e clique "
                    "em um recurso na prévia."
                )
            )
            note = ttk.Label(
                box,
                textvariable=self.resource_note,
                wraplength=600,
            )
            note.pack(anchor="w", pady=(5, 0))

            box.bind(
                "<Configure>",
                lambda event: note.configure(
                    wraplength=max(220, event.width-16)
                ),
            )
            self.preview_canvas.bind(
                "<Button-1>",
                self.select_resource,
                add="+",
            )

        def toggle_resource_mode(self):
            self.resource_mode = not self.resource_mode

            self.resource_button.configure(
                text=(
                    "Sair da marcação"
                    if self.resource_mode
                    else "Marcar recurso esgotado"
                )
            )
            self.preview_canvas.configure(
                cursor="crosshair" if self.resource_mode else ""
            )
            self.resource_note.set(
                "Clique no recurso e confirme o objeto esgotado."
                if self.resource_mode
                else "Marcação manual desativada."
            )

        def resource_action(
            self, ids=None, undo=False,
            restore=False, digest=None
        ):
            if not self.resource_view:
                self.resource_note.set(
                    "Abra um replay e aguarde a prévia."
                )
                return

            current = self.resource_view["digest"]

            if digest is not None and digest != current:
                self.resource_note.set(
                    "A partida mudou. Selecione novamente o recurso."
                )
                return

            if restore and not messagebox.askyesno(
                "Restaurar marcadores",
                "Restaurar todas as marcações manuais deste replay?",
                parent=self.root,
            ):
                return

            try:
                changed = store.change(
                    current, ids, undo, restore
                )
                self.next_frame = 0

                self.resource_note.set(
                    "Anotação salva. A exibição será atualizada."
                    if changed else
                    "Nenhuma alteração a desfazer ou aplicar."
                )

            except Exception as error:
                messagebox.showerror(
                    "Não foi possível salvar",
                    str(error),
                    parent=self.root,
                )

        def select_resource(self, event):
            if not self.resource_mode:
                return

            if (
                not self.resource_view
                or not self.central_raw
                or not getattr(self, "central_photo", None)
            ):
                self.resource_note.set(
                    "Aguarde uma prévia válida."
                )
                return

            iw = self.central_photo.width()
            ih = self.central_photo.height()

            left = (
                self.preview_canvas.winfo_width() - iw
            ) / 2
            top = (
                self.preview_canvas.winfo_height() - ih
            ) / 2

            if not (
                left <= event.x <= left + iw
                and top <= event.y <= top + ih
            ):
                return

            x = (event.x-left) * 900 / iw
            y = (event.y-top) * 450 / ih

            matches = sorted(
                [
                    (
                        (point["px"]-x)**2
                        + (point["py"]-y)**2,
                        point,
                    )
                    for point in self.resource_view["points"]
                ],
                key=lambda item: item[0],
            )
            candidates = [
                point for distance, point in matches
                if distance <= 24**2
            ][:10]

            if not candidates:
                self.resource_note.set(
                    "Nenhum recurso identificável próximo. "
                    "Tente clicar mais perto."
                )
                return

            digest = self.resource_view["digest"]

            popup = tk.Toplevel(self.root)
            popup.title("Confirmar marcação manual")
            popup.transient(self.root)
            popup.geometry("620x360")
            popup.configure(bg=BG)
            popup.grab_set()
            popup.bind(
                "<Escape>",
                lambda event: popup.destroy(),
            )

            ttk.Label(
                popup,
                text=(
                    "Escolha o objeto que você verificou como esgotado.\n"
                    "Esta ação é uma anotação manual, "
                    "não uma detecção do jogo."
                ),
                wraplength=580,
            ).pack(anchor="w", padx=16, pady=12)

            items = tk.Listbox(
                popup,
                exportselection=False,
                height=8,
                bg=CARD,
                fg=TEXT,
                selectbackground=BRONZE,
                selectforeground=BG,
                highlightbackground=EDGE,
                font=(self.body_font, 11),
            )

            for point in candidates:
                items.insert(
                    "end",
                    f"{point['name']} · ID {point['id']} · "
                    f"({point['x']:.1f}, {point['y']:.1f})",
                )

            items.pack(
                fill="both", expand=True, padx=16
            )
            items.selection_set(0)

            def confirm():
                selected = items.curselection()

                if selected:
                    self.resource_action(
                        ids=[candidates[selected[0]]["id"]],
                        digest=digest,
                    )
                    popup.destroy()

            row = ttk.Frame(popup)
            row.pack(fill="x", padx=16, pady=12)

            ttk.Button(
                row,
                text="Confirmar esgotado",
                command=confirm,
            ).pack(side="left")

            ttk.Button(
                row,
                text="Cancelar",
                command=popup.destroy,
            ).pack(side="right")

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
            if "recursos_manuais.py" not in nomes:
                node.elts.append(
                    ast.Constant("recursos_manuais.py")
                )

        return node


def main():
    pasta = Path(__file__).resolve().parent

    for nome in (
        "painel_jogadores.py",
        "central_replay.py",
        "gerar_instalador.py",
        "gaia_minimapa.py",
    ):
        if not (pasta / nome).is_file():
            raise RuntimeError(
                "Arquivo ausente: " + nome
                + ". Aplique primeiro a atualização Gaia."
            )

    alterados = {"recursos_manuais.py": MODULO.lstrip()}

    texto = (pasta / "painel_jogadores.py").read_text(
        encoding="utf-8-sig"
    )

    if "_ativar_recursos_manuais(globals())" not in texto:
        integracao = (
            "from recursos_manuais import ativar "
            "as _ativar_recursos_manuais\n"
            "_ativar_recursos_manuais(globals())\n\n"
        )

        texto, quantidade = re.subn(
            r"(?m)^from central_replay import ativar.*$",
            lambda resultado: integracao + resultado.group(),
            texto,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Integração da central não reconhecida."
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
                        isinstance(item, ast.Call)
                        and ast.unparse(item.func)
                        == "self.resource_controls"
                        for item in ast.walk(metodo)
                    )

                    if not existe:
                        metodo.body.append(ast.parse(
                            "self.resource_controls()"
                        ).body[0])

    if quantidade != 1:
        raise RuntimeError(
            "Central diferente do esperado."
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
        raise RuntimeError(
            "Gerador diferente do esperado."
        )

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
                    topico[0] == "Marcar recursos esgotados"
                    for topico in topicos
                ):
                    topicos.append((
                        "Marcar recursos esgotados",
                        (
                            "Esta função é manual e não reconhece "
                            "automaticamente o esgotamento.\n\n"
                            "No PC, ative Marcar recurso esgotado, "
                            "clique na prévia, escolha o objeto na "
                            "lista e confirme.\n\n"
                            "O marcador será ocultado no PC e, no "
                            "próximo quadro, no overlay e celular.\n\n"
                            "Desfazer reverte as últimas operações. "
                            "Restaurar marcadores recupera as marcações "
                            "do replay atual.\n\n"
                            "As anotações ficam em recursos_marcados.json, "
                            "separadas por replay. Não alteram o arquivo "
                            "do jogo nem corrigem contagens ou estados "
                            "internos. Podem ser desfeitas até 100 "
                            "operações recentes."
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

    print("\nMarcação manual de recursos preparada.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.5 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)