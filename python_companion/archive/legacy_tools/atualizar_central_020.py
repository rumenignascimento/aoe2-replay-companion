import ast
from datetime import datetime
import io
from pathlib import Path
import re
import shutil


CENTRAL = r'''
import copy
import io
import time
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageChops, ImageDraw, ImageTk

BG = "#171a1a"
CARD = "#202424"
EDGE = "#514737"
TEXT = "#eee4d4"
MUTED = "#b8b6ac"
BRONZE = "#b88a4e"

CORNERS = (
    "Superior esquerdo", "Superior direito",
    "Inferior esquerdo", "Inferior direito",
)


def ativar(g):
    if g.get("_central_replay_ativa"):
        return
    g["_central_replay_ativa"] = True

    p, mini, app = g["p"], g["mini"], g["app"]
    p.CONFIG_DEFAULTS.update(
        central_buildings=True,
        central_icon_size=int(mini.MAP_ICON_SIZE),
    )

    old_validate = p._validate_config

    def validate(values):
        result = old_validate(values)
        value = result["central_icon_size"]
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 6 <= value <= 48
        ):
            raise ValueError(
                "Ícones do minimapa: use um inteiro entre 6 e 48."
            )
        return result

    p._validate_config = validate
    layers = [True, int(mini.MAP_ICON_SIZE)]
    old_render = app.map_svg

    def render(session):
        buildings, size = getattr(
            g["CONTEXT"], "central_layers", tuple(layers)
        )
        proxy = session

        if not buildings:
            proxy = copy.copy(session)
            proxy.model = dict(session.model)
            proxy.model["points"] = [
                obj for obj in session.model["points"]
                if obj["kind"] != "centros"
            ]
            proxy.initial = [
                obj for obj in session.initial
                if obj["kind"] != "building"
            ]
            proxy.build_requests = []
            proxy._full_session = proxy

        previous = mini.MAP_ICON_SIZE
        mini.MAP_ICON_SIZE = size

        try:
            return old_render(proxy)
        finally:
            mini.MAP_ICON_SIZE = previous

    app.map_svg = render
    mini.minimap_svg = render
    g["selected_map"] = render

    # Uma renderização maior alimenta a prévia central.
    # A imagem enviada ao overlay mantém a largura escolhida.
    old_frame = app.frame

    def frame(session, directory, width):
        data = old_frame(session, directory, 900)
        data["central_png"] = data["png"]

        if width != 900:
            image = Image.open(
                io.BytesIO(data["png"])
            ).convert("RGB")
            diff = ImageChops.difference(
                image,
                Image.new("RGB", image.size, (255, 0, 255)),
            )
            a, b, c = diff.split()
            mask = ImageChops.lighter(
                ImageChops.lighter(a, b), c
            ).point(lambda value: 255 if value else 0)

            image.putalpha(mask)
            image = image.resize(
                (width, max(1, round(width / 2))),
                Image.Resampling.LANCZOS,
            )
            opaque = Image.composite(
                image.convert("RGB"),
                Image.new("RGB", image.size, (255, 0, 255)),
                image.getchannel("A").point(
                    lambda value: 255 if value >= 128 else 0
                ),
            )
            output = io.BytesIO()
            opaque.save(output, format="PNG")
            data["png"] = output.getvalue()

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
            window = self.window

            if epoch == window.epoch and kind == "ok":
                window.central_raw = data.get(
                    "central_png", data["png"]
                )
                window.central_updated = time.monotonic()
                window.central_generation += 1
                window.central_map = session.model.get(
                    "map", "Mapa"
                )
                window.central_ms = session.ms

            return result

    class Window(Base):
        def __init__(self, root, native):
            self.central_buildings = tk.BooleanVar(
                master=root, value=True
            )
            self.central_icon_size = tk.IntVar(
                master=root, value=int(mini.MAP_ICON_SIZE)
            )
            self._central_ready = False

            super().__init__(root, native)

            self.central_raw = None
            self.central_generation = 0
            self.central_updated = 0
            self.central_map = "Nenhum replay aberto"
            self.central_ms = 0
            self.preview_key = None
            self.queue = Queue(self.queue, self)
            self.scroll_panels = []
            self.central_nav = "Visão geral"

            self.central_buildings.trace_add(
                "write", self.central_layers
            )
            self.central_icon_size.trace_add(
                "write", self.central_layers
            )
            self.central_layers()

            # Mantém os componentes internos que sustentam
            # o leitor, as configurações e os overlays.
            for child in root.winfo_children():
                if not isinstance(child, (tk.Toplevel, tk.Menu)):
                    child.pack_forget()
                    child.grid_forget()

            self.theme()
            self.build_central()
            self._central_ready = True

            root.title("AoE II · Replay Companion")
            root.geometry(
                f"{min(1440, root.winfo_screenwidth()-60)}"
                f"x{min(920, root.winfo_screenheight()-80)}"
            )
            root.minsize(1000, 650)
            root.bind("<MouseWheel>", self.wheel)
            root.after(200, self.central_tick)

        def central_layers(self, *args):
            try:
                size = int(self.central_icon_size.get())
                if not 6 <= size <= 48:
                    return
                layers[:] = [
                    bool(self.central_buildings.get()), size
                ]
            except (ValueError, tk.TclError):
                return
            self.next_frame = 0

        def apply_settings(self, values):
            warning = super().apply_settings(values)
            self.central_layers()
            return warning

        def change_player(self, *args):
            previous = g["SELECTION"]
            super().change_player(*args)

            if (
                self._central_ready
                and previous != g["SELECTION"]
            ):
                self.central_raw = None
                self.preview_key = None

        def attach(self, *args, **kwargs):
            if self._central_ready:
                self.central_raw = None
                self.preview_key = None
            return super().attach(*args, **kwargs)

        def job(self, *args, **kwargs):
            g["CONTEXT"].central_layers = tuple(layers)
            try:
                return super().job(*args, **kwargs)
            finally:
                del g["CONTEXT"].central_layers

        def theme(self):
            families = {
                name.lower()
                for name in tkfont.families(self.root)
            }
            self.body_font = (
                "Segoe UI" if "segoe ui" in families
                else "Helvetica"
            )
            self.title_font = (
                "Georgia" if "georgia" in families
                else "Palatino"
            )
            self.code_font = (
                "Consolas" if "consolas" in families
                else "Courier"
            )

            self.root.configure(bg=BG)
            style = ttk.Style(self.root)
            style.theme_use("clam")

            style.configure(
                ".", background=CARD, foreground=TEXT,
                font=(self.body_font, 10),
            )
            style.configure("TFrame", background=BG)
            style.configure("Card.TFrame", background=CARD)
            style.configure(
                "TLabel", background=CARD, foreground=TEXT
            )
            style.configure(
                "TButton",
                background="#34332c", foreground=TEXT,
                bordercolor=EDGE, lightcolor=EDGE,
                darkcolor=EDGE, focuscolor=BRONZE,
                padding=(10, 7),
            )
            style.map(
                "TButton",
                background=[
                    ("active", "#514432"),
                    ("pressed", "#775735"),
                ],
            )
            style.configure(
                "Accent.TButton",
                background="#795a32", foreground="#fff0d8",
            )
            style.configure(
                "TEntry",
                fieldbackground="#282d2c",
                foreground=TEXT, insertcolor=TEXT,
            )
            style.configure(
                "TCombobox",
                fieldbackground="#282d2c",
                foreground=TEXT, arrowcolor=BRONZE,
            )
            style.map(
                "TCombobox",
                fieldbackground=[("readonly", "#282d2c")],
                foreground=[("readonly", TEXT)],
            )
            style.configure(
                "TSpinbox",
                fieldbackground="#282d2c",
                foreground=TEXT, arrowcolor=BRONZE,
            )
            style.configure(
                "TScale",
                background=CARD, troughcolor="#3b3e38",
            )
            style.configure(
                "TNotebook", background=CARD, borderwidth=0
            )
            style.configure(
                "TNotebook.Tab",
                background="#2b2e2a",
                foreground=TEXT, padding=(14, 8),
            )
            style.map(
                "TNotebook.Tab",
                background=[("selected", "#795a32")],
            )
            style.configure(
                "TLabelframe",
                background=CARD, bordercolor=EDGE,
            )
            style.configure(
                "TLabelframe.Label",
                background=CARD, foreground=TEXT,
            )

            self.toggle_images = []
            for selected in (False, True):
                image = Image.new("RGBA", (40, 22))
                draw = ImageDraw.Draw(image)
                draw.rounded_rectangle(
                    (0, 0, 39, 21),
                    radius=11,
                    fill=BRONZE if selected else "#555a54",
                )
                x = 20 if selected else 2
                draw.ellipse(
                    (x, 2, x + 17, 19), fill="#f5ead5"
                )
                self.toggle_images.append(
                    ImageTk.PhotoImage(image, master=self.root)
                )

            style.element_create(
                "Replay.Toggle", "image",
                self.toggle_images[0],
                ("selected", self.toggle_images[1]),
            )
            style.layout(
                "Switch.TCheckbutton",
                [
                    (
                        "Checkbutton.padding",
                        {
                            "sticky": "nswe",
                            "children": [
                                (
                                    "Replay.Toggle",
                                    {"side": "left", "sticky": "w"},
                                ),
                                (
                                    "Checkbutton.label",
                                    {"side": "left", "sticky": "w"},
                                ),
                            ],
                        },
                    )
                ],
            )
            style.configure(
                "Switch.TCheckbutton",
                background=CARD, foreground=TEXT, padding=5,
            )

        def card(self, parent, title=None):
            box = tk.Frame(
                parent, bg=CARD,
                highlightbackground=EDGE,
                highlightthickness=1,
            )
            if title:
                tk.Label(
                    box, text=title, bg=CARD, fg=TEXT,
                    font=(self.title_font, 16, "bold"),
                    anchor="w",
                ).pack(
                    fill="x", padx=14, pady=(12, 8)
                )
            return box

        def scrollbox(self, parent):
            shell = ttk.Frame(
                parent, style="Card.TFrame"
            )
            shell.pack(fill="both", expand=True)

            canvas = tk.Canvas(
                shell, bg=CARD, highlightthickness=0
            )
            bar = ttk.Scrollbar(
                shell, orient="vertical",
                command=canvas.yview,
            )
            canvas.configure(yscrollcommand=bar.set)
            bar.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)

            body = ttk.Frame(
                canvas, style="Card.TFrame", padding=12
            )
            item = canvas.create_window(
                0, 0, window=body, anchor="nw"
            )

            body.bind(
                "<Configure>",
                lambda event: canvas.configure(
                    scrollregion=canvas.bbox("all")
                ),
            )
            canvas.bind(
                "<Configure>",
                lambda event: canvas.itemconfigure(
                    item, width=event.width
                ),
            )

            self.scroll_panels.append((shell, canvas))
            return body

        def wheel(self, event):
            widget = event.widget
            if widget.winfo_toplevel() != self.root:
                return

            for shell, canvas in self.scroll_panels:
                node = widget
                while node is not None:
                    if node == shell:
                        canvas.yview_scroll(
                            -1 if event.delta > 0 else 1,
                            "units",
                        )
                        return "break"
                    node = getattr(node, "master", None)

        def field(
            self, parent, label, variable,
            values=None, bounds=None
        ):
            row = ttk.Frame(parent, style="Card.TFrame")
            row.pack(fill="x", pady=6)
            ttk.Label(row, text=label).pack(
                anchor="w", pady=(0, 4)
            )

            if values is not None:
                widget = ttk.Combobox(
                    row, textvariable=variable,
                    values=values, state="readonly",
                )
            elif bounds:
                widget = ttk.Spinbox(
                    row, textvariable=variable,
                    from_=bounds[0], to=bounds[1],
                    increment=1,
                    command=self.refresh_central,
                )
            else:
                widget = ttk.Entry(
                    row, textvariable=variable
                )

            widget.pack(fill="x")
            widget.bind(
                "<Return>",
                lambda event: self.refresh_central(),
            )
            widget.bind(
                "<FocusOut>",
                lambda event: self.refresh_central(),
            )
            return widget

        def switch(self, parent, label, variable):
            ttk.Checkbutton(
                parent,
                text="  " + label,
                variable=variable,
                style="Switch.TCheckbutton",
                command=self.refresh_central,
            ).pack(anchor="w", pady=3)

        def refresh_central(self, *args):
            self.next_frame = 0
            self.preview_key = None

        def build_central(self):
            shell = tk.Frame(self.root, bg=BG)
            shell.pack(fill="both", expand=True)

            top = tk.Frame(shell, bg="#202321", height=62)
            top.pack(fill="x")

            tk.Label(
                top, text="II", bg="#65372a", fg="#f3cd83",
                font=(self.title_font, 22, "bold"), padx=12,
            ).pack(side="left", padx=(18, 12), pady=10)

            tk.Label(
                top,
                text="AoE II · Replay Companion",
                bg="#202321", fg=TEXT,
                font=(self.title_font, 19, "bold"),
            ).pack(side="left")

            ttk.Button(
                top, text="Abrir replay",
                style="Accent.TButton",
                command=self.choose_file,
            ).pack(side="right", padx=16)

            ttk.Button(
                top, text="Pasta savegame",
                command=self.choose_folder,
            ).pack(side="right")

            self.monitor_label = tk.Label(
                top, bg="#202321", fg="#94be7d",
                text="● Sem monitoramento",
            )
            self.monitor_label.pack(side="right", padx=16)

            foot = tk.Frame(shell, bg="#202321")
            foot.pack(side="bottom", fill="x")

            ttk.Button(
                foot, text="Alterar pasta",
                command=self.choose_folder,
            ).pack(side="right", padx=10, pady=6)

            tk.Label(
                foot, textvariable=self.status,
                bg="#202321", fg=MUTED,
                anchor="w", wraplength=1000,
            ).pack(
                side="left", padx=16,
                fill="x", expand=True,
            )

            body = tk.Frame(shell, bg=BG)
            body.pack(fill="both", expand=True)

            side = tk.Frame(
                body, bg="#1e2221", width=180
            )
            side.pack(side="left", fill="y")
            side.pack_propagate(False)

            tk.Label(
                side, text="CENTRAL DE REPLAY",
                bg="#1e2221", fg=BRONZE,
                font=(self.body_font, 9, "bold"),
            ).pack(anchor="w", padx=16, pady=20)

            self.nav_buttons = {}
            for name in (
                "Visão geral", "Overlay", "Minimapa", "Ordens"
            ):
                button = tk.Button(
                    side, text=name,
                    command=lambda n=name: self.navigate(n),
                    bg="#1e2221", fg=TEXT,
                    activebackground="#514432",
                    activeforeground=TEXT,
                    bd=0, highlightthickness=0,
                    anchor="w", padx=18, pady=14,
                    font=(self.body_font, 12),
                )
                button.pack(fill="x", pady=2)
                self.nav_buttons[name] = button

            ttk.Button(
                side, text="Configurações",
                command=lambda: self.navigate("Configurações"),
            ).pack(
                side="bottom", fill="x", padx=12, pady=14
            )

            ttk.Button(
                side, text="Atalhos",
                command=self.keys_dialog,
            ).pack(side="bottom", fill="x", padx=12)

            right = self.card(body, "Overlay")
            right.pack(
                side="right", fill="y",
                padx=(0, 16), pady=16,
            )
            right.configure(width=290)
            right.pack_propagate(False)

            controls = self.scrollbox(right)
            self.switch(
                controls, "Exibir overlay", self.show
            )

            tabs = ttk.Notebook(controls)
            tabs.pack(fill="x", pady=10)
            appearance = ttk.Frame(
                tabs, style="Card.TFrame", padding=8
            )
            position = ttk.Frame(
                tabs, style="Card.TFrame", padding=8
            )
            tabs.add(appearance, text="Aparência")
            tabs.add(position, text="Posição")

            self.field(
                appearance, "Largura (px)",
                self.width, bounds=(300, 900),
            )
            ttk.Scale(
                appearance, from_=300, to=900,
                variable=self.width,
                command=lambda value: self.resize(),
            ).pack(fill="x")

            ttk.Label(
                appearance, text="Opacidade"
            ).pack(anchor="w", pady=(12, 4))

            ttk.Scale(
                appearance, from_=.2, to=1,
                variable=self.opacity, command=self.alpha,
            ).pack(fill="x")

            self.opacity_label = ttk.Label(appearance)
            self.opacity_label.pack(anchor="e")

            self.field(
                position, "Posição", self.position_corner,
                values=CORNERS,
            )
            self.field(
                position, "Margem X (px)",
                self.position_x, bounds=(0, 10000),
            )
            self.field(
                position, "Margem Y (px)",
                self.position_y, bounds=(0, 10000),
            )

            ttk.Button(
                controls, text="Testar por 10 segundos",
                style="Accent.TButton",
                command=self.preview,
            ).pack(fill="x", pady=12)

            ttk.Label(
                controls,
                text="Ctrl + Alt + M\nExibir ou ocultar o overlay.",
                wraplength=230,
            ).pack(anchor="w", pady=8)

            ttk.Button(
                controls,
                text="Celular / tablet · QR Code",
                command=lambda: self.mobile_dialog(),
            ).pack(fill="x", pady=10)

            ttk.Button(
                controls, text="Salvar configurações",
                command=self.save_settings,
            ).pack(fill="x", pady=6)

            center = tk.Frame(body, bg=BG)
            center.pack(
                fill="both", expand=True,
                padx=16, pady=16,
            )

            self.page_title = tk.Label(
                center, text="Visão geral",
                bg=BG, fg=TEXT,
                font=(self.title_font, 26, "bold"),
                anchor="w",
            )
            self.page_title.pack(fill="x")

            self.meta = tk.Label(
                center,
                text="Mapa inicial e ordens do replay.",
                bg=BG, fg=MUTED, anchor="w",
            )
            self.meta.pack(fill="x", pady=(4, 12))

            self.overview = tk.Frame(center, bg=BG)
            self.map_card = self.card(self.overview)
            self.map_card.pack(fill="both", expand=True)

            heading = tk.Frame(self.map_card, bg=CARD)
            heading.pack(fill="x", padx=14, pady=10)

            tk.Label(
                heading, text="Prévia do minimapa",
                bg=CARD, fg=TEXT,
                font=(self.title_font, 16, "bold"),
            ).pack(side="left")

            self.central_players = ttk.Combobox(
                heading, textvariable=self.display_player,
                state="readonly", width=17,
            )
            self.central_players.pack(side="right")

            summary = tk.Frame(self.map_card, bg=CARD)
            summary.pack(
                side="bottom", fill="x",
                padx=12, pady=10,
            )
            self.summary_labels = []

            for text in (
                "Construções", "Produção", "Pesquisas"
            ):
                label = tk.Label(
                    summary, text="0 " + text,
                    bg="#2a2f2b", fg=TEXT, pady=10,
                    font=(self.body_font, 10),
                )
                label.pack(
                    side="left", fill="x",
                    expand=True, padx=3,
                )
                self.summary_labels.append(label)

            self.preview_canvas = tk.Canvas(
                self.map_card,
                bg="#181d1b", highlightthickness=0,
                height=300,
            )
            self.preview_canvas.pack(
                fill="both", expand=True, padx=10
            )
            self.preview_canvas.bind(
                "<Configure>",
                lambda event: setattr(
                    self, "preview_key", None
                ),
            )

            layer_card = self.card(
                self.overview, "Camadas e informações"
            )
            layer_card.pack(fill="x", pady=(12, 0))

            rows = ttk.Frame(
                layer_card, style="Card.TFrame"
            )
            rows.pack(
                fill="x", padx=10, pady=(0, 10)
            )

            left = ttk.Frame(rows, style="Card.TFrame")
            left.pack(
                side="left", expand=True, fill="x"
            )
            other = ttk.Frame(rows, style="Card.TFrame")
            other.pack(
                side="left", expand=True, fill="x"
            )

            self.switch(left, "Terreno", self.map_terrain)
            self.switch(
                left, "Deslocamentos", self.troops_map
            )
            self.switch(
                other, "Construções", self.central_buildings
            )
            self.switch(
                other, "Pesquisas e eras", self.research_icons
            )

            self.advanced = self.card(self.overview)
            self.advanced_body = self.scrollbox(self.advanced)

            self.orders_page = self.card(
                center, "Ordens registradas"
            )
            order_heading = ttk.Frame(
                self.orders_page,
                style="Card.TFrame", padding=10,
            )
            order_heading.pack(fill="x")

            self.order_players = ttk.Combobox(
                order_heading,
                textvariable=self.display_player,
                state="readonly",
            )
            self.order_players.pack(side="left")

            ttk.Button(
                order_heading, text="Abrir relatórios",
                command=self.open_output,
            ).pack(side="right")

            self.orders_text = tk.Text(
                self.orders_page,
                bg="#1b201e", fg=TEXT,
                insertbackground=TEXT,
                wrap="word",
                font=(self.code_font, 10),
                bd=0,
            )
            bar = ttk.Scrollbar(
                self.orders_page,
                command=self.orders_text.yview,
            )
            bar.pack(side="right", fill="y")
            self.orders_text.configure(
                yscrollcommand=bar.set
            )
            self.orders_text.pack(
                fill="both", expand=True,
                padx=10, pady=10,
            )

            self.settings_page = self.card(
                center, "Configurações"
            )
            settings = self.scrollbox(self.settings_page)

            self.field(
                settings, "Pasta savegame monitorada",
                self.folder,
            ).configure(state="readonly")

            for text, command in (
                (
                    "Alterar pasta / monitorar",
                    self.choose_folder,
                ),
                ("Salvar configurações", self.save_settings),
                (
                    "Restaurar configurações originais",
                    self.restore_settings,
                ),
                (
                    "Configurar atalhos de jogadores",
                    self.keys_dialog,
                ),
                (
                    "Conectar celular / tablet",
                    lambda: self.mobile_dialog(),
                ),
            ):
                ttk.Button(
                    settings, text=text, command=command
                ).pack(anchor="w", pady=6)

            ttk.Label(
                settings,
                text=(
                    "Os números representam pedidos registrados. "
                    "Não confirmam conclusões, unidades vivas "
                    "ou posições atuais.\n"
                    "A atualização tem alvo de 1 segundo e aguarda "
                    "o processamento anterior terminar."
                ),
                wraplength=520,
            ).pack(anchor="w", pady=16)

            self.navigate("Visão geral")

        def navigate(self, name):
            self.central_nav = name
            self.page_title.configure(text=name)

            for page in (
                self.overview, self.orders_page,
                self.settings_page, self.advanced,
            ):
                page.pack_forget()

            for key, button in self.nav_buttons.items():
                button.configure(
                    bg="#5b452e" if key == name else "#1e2221"
                )

            if name == "Ordens":
                self.orders_page.pack(
                    fill="both", expand=True
                )
            elif name == "Configurações":
                self.settings_page.pack(
                    fill="both", expand=True
                )
            else:
                self.overview.pack(fill="both", expand=True)

                if name in ("Minimapa", "Overlay"):
                    self.advanced.pack(
                        fill="x", pady=(10, 0)
                    )
                    self.advanced.configure(height=220)
                    self.advanced.pack_propagate(False)

                    for child in (
                        self.advanced_body.winfo_children()
                    ):
                        child.destroy()

                    parent = self.advanced_body

                    if name == "Minimapa":
                        self.field(
                            parent, "Rotação", self.map_turn,
                            values=(
                                "0°", "90°", "180°", "270°"
                            ),
                        )
                        self.switch(
                            parent, "Espelhar mapa",
                            self.map_mirror,
                        )
                        self.field(
                            parent,
                            "Ícones das construções (px)",
                            self.central_icon_size,
                            bounds=(6, 48),
                        )
                        self.field(
                            parent, "Ícones das tropas (px)",
                            self.troops_icon_size,
                            bounds=(10, 40),
                        )
                        self.field(
                            parent,
                            "Intervalo visível das ordens (segundos)",
                            self.troops_seconds,
                            bounds=(5, 300),
                        )
                        self.switch(
                            parent,
                            "Possíveis aberturas nas paliçadas",
                            self.wall_endpoints,
                        )
                    else:
                        self.switch(
                            parent, "Exibir barra de pedidos",
                            self.caption_show,
                        )
                        self.switch(
                            parent, "Produção militar na barra",
                            self.troops_bar,
                        )
                        self.field(
                            parent, "Posição da barra",
                            self.caption_corner,
                            values=CORNERS,
                        )
                        self.field(
                            parent, "Margem X da barra",
                            self.caption_x,
                            bounds=(0, 10000),
                        )
                        self.field(
                            parent, "Margem Y da barra",
                            self.caption_y,
                            bounds=(0, 10000),
                        )
                        self.field(
                            parent, "Tamanho dos ícones da barra",
                            self.bar_size,
                            bounds=(24, 120),
                        )
                        ttk.Label(
                            parent, text="Opacidade da barra"
                        ).pack(anchor="w")
                        ttk.Scale(
                            parent, from_=.2, to=1,
                            variable=self.bar_opacity,
                        ).pack(fill="x")

            self.preview_key = None

        def central_tick(self):
            if self.closing:
                return

            try:
                values = ["Todos"] + [
                    f"Jogador {number}"
                    for number in self.players
                ]
                for widget in (
                    self.central_players,
                    self.order_players,
                ):
                    widget.configure(values=values)

                monitoring = bool(self.folder.get())
                self.monitor_label.configure(
                    text=(
                        "● Monitorando savegame"
                        if monitoring else
                        "● Abra um replay ou selecione a pasta"
                    ),
                    fg="#94be7d" if monitoring else MUTED,
                )

                ago = (
                    int(
                        time.monotonic()
                        - self.central_updated
                    )
                    if self.central_updated else None
                )
                self.meta.configure(
                    text=(
                        f"{self.central_map}  ·  Replay até "
                        f"{app.base.game_time(self.central_ms)}"
                        + (
                            f"  ·  Atualizado há {ago}s"
                            if ago is not None else ""
                        )
                    )
                )
                self.opacity_label.configure(
                    text=f"{float(self.opacity.get()):.0%}"
                )

                state = self.bar_state.get("per_player", [])
                totals = [
                    sum(
                        sum(
                            int(value) for value in player.get(
                                "building_counts", {}
                            ).values()
                        )
                        for player in state
                    ),
                    sum(
                        sum(
                            int(value) for value in player.get(
                                "military_orders", {}
                            ).values()
                        )
                        for player in state
                    ),
                    sum(
                        sum(
                            int(record["requests"])
                            for record in player.get(
                                "research_orders", []
                            )
                        )
                        for player in state
                    ),
                ]

                for label, count, name in zip(
                    self.summary_labels, totals,
                    ("construções", "produção", "pesquisas"),
                ):
                    label.configure(
                        text=f"{count} pedidos · {name}"
                    )

                if (
                    getattr(self, "orders_generation", None)
                    != self.central_generation
                ):
                    self.orders_generation = (
                        self.central_generation
                    )
                    self.orders_text.configure(state="normal")
                    self.orders_text.delete("1.0", "end")
                    self.orders_text.insert(
                        "1.0", self.report.get("1.0", "end")
                    )
                    self.orders_text.configure(state="disabled")

                width = max(
                    1, self.preview_canvas.winfo_width()
                )
                height = max(
                    1, self.preview_canvas.winfo_height()
                )
                key = (
                    self.central_generation,
                    width, height,
                    self.central_raw is not None,
                )

                if key != self.preview_key:
                    self.preview_key = key
                    self.preview_canvas.delete("all")

                    if self.central_raw:
                        image = Image.open(
                            io.BytesIO(self.central_raw)
                        ).convert("RGB")

                        diff = ImageChops.difference(
                            image,
                            Image.new(
                                "RGB", image.size,
                                (255, 0, 255),
                            ),
                        )
                        a, b, c = diff.split()
                        mask = ImageChops.lighter(
                            ImageChops.lighter(a, b), c
                        ).point(
                            lambda value: 255 if value else 0
                        )
                        image = Image.composite(
                            image,
                            Image.new(
                                "RGB", image.size, "#181d1b"
                            ),
                            mask,
                        )
                        scale = min(
                            max(1, width-12) / image.width,
                            max(1, height-12) / image.height,
                        )
                        image = image.resize(
                            (
                                max(1, round(image.width*scale)),
                                max(1, round(image.height*scale)),
                            ),
                            Image.Resampling.LANCZOS,
                        )
                        self.central_photo = (
                            ImageTk.PhotoImage(
                                image, master=self.root
                            )
                        )
                        self.preview_canvas.create_image(
                            width/2, height/2,
                            image=self.central_photo,
                        )
                    else:
                        self.preview_canvas.create_text(
                            width/2, height/2,
                            text=(
                                "Abra um replay para visualizar "
                                "o mapa\nou monitore a pasta savegame."
                            ),
                            fill=MUTED,
                            font=(self.body_font, 13),
                            justify="center",
                        )

            except tk.TclError:
                if not self.root.winfo_exists():
                    return
            finally:
                if not self.closing:
                    self.root.after(200, self.central_tick)

    g["Window"] = Window
'''


PINCA = r'''
const touchMap = document.getElementById('viewport');
const touchImage = document.getElementById('map');
const touchSlider = document.getElementById('zoom');
const touchOutput = document.getElementById('zoomValue');
const minimapPointers = new Map();

let minimapGesture = null;
let minimapZoom = Number(touchSlider.value) || 100;

touchSlider.step = '1';
touchImage.draggable = false;

function setMinimapZoom(value, center, anchor) {
    const next = Math.min(
        Number(touchSlider.max) || 300,
        Math.max(
            Number(touchSlider.min) || 100,
            Math.round(value)
        )
    );

    center = center || {
        x: touchMap.clientWidth / 2,
        y: touchMap.clientHeight / 2
    };
    anchor = anchor || {
        x: (touchMap.scrollLeft + center.x) /
           (minimapZoom / 100),
        y: (touchMap.scrollTop + center.y) /
           (minimapZoom / 100)
    };

    minimapZoom = next;
    touchSlider.value = String(next);
    touchImage.style.width = next + '%';
    touchOutput.textContent = next + '%';

    touchMap.scrollLeft =
        anchor.x * (next / 100) - center.x;
    touchMap.scrollTop =
        anchor.y * (next / 100) - center.y;
}

touchSlider.oninput = () =>
    setMinimapZoom(Number(touchSlider.value));

function beginMinimapGesture() {
    const points = [...minimapPointers.values()];

    if (points.length >= 2) {
        const a = points[0], b = points[1];
        const rect = touchMap.getBoundingClientRect();
        const center = {
            x: (a.x + b.x) / 2 - rect.left,
            y: (a.y + b.y) / 2 - rect.top
        };

        minimapGesture = {
            type: 'pinch',
            distance: Math.max(
                1, Math.hypot(a.x-b.x, a.y-b.y)
            ),
            zoom: minimapZoom,
            anchor: {
                x: (touchMap.scrollLeft + center.x) /
                   (minimapZoom / 100),
                y: (touchMap.scrollTop + center.y) /
                   (minimapZoom / 100)
            }
        };
    } else if (points.length === 1) {
        minimapGesture = {
            type: 'pan',
            x: points[0].x,
            y: points[0].y,
            left: touchMap.scrollLeft,
            top: touchMap.scrollTop
        };
    } else {
        minimapGesture = null;
    }
}

touchMap.addEventListener('pointerdown', event => {
    if (
        event.pointerType === 'mouse' &&
        event.button !== 0
    ) return;

    minimapPointers.set(event.pointerId, {
        x: event.clientX, y: event.clientY
    });

    try {
        touchMap.setPointerCapture(event.pointerId);
    } catch (error) {}

    touchMap.classList.add('map-dragging');
    beginMinimapGesture();
    event.preventDefault();
});

touchMap.addEventListener('pointermove', event => {
    if (!minimapPointers.has(event.pointerId)) return;

    minimapPointers.set(event.pointerId, {
        x: event.clientX, y: event.clientY
    });

    const points = [...minimapPointers.values()];

    if (
        points.length >= 2 &&
        minimapGesture?.type === 'pinch'
    ) {
        const a = points[0], b = points[1];
        const rect = touchMap.getBoundingClientRect();

        setMinimapZoom(
            minimapGesture.zoom *
            Math.hypot(a.x-b.x, a.y-b.y) /
            minimapGesture.distance,
            {
                x: (a.x+b.x)/2 - rect.left,
                y: (a.y+b.y)/2 - rect.top
            },
            minimapGesture.anchor
        );
    } else if (
        points.length === 1 &&
        minimapGesture?.type === 'pan'
    ) {
        touchMap.scrollLeft =
            minimapGesture.left -
            (points[0].x - minimapGesture.x);

        touchMap.scrollTop =
            minimapGesture.top -
            (points[0].y - minimapGesture.y);
    }
});

function endMinimapPointer(event) {
    minimapPointers.delete(event.pointerId);
    beginMinimapGesture();

    if (!minimapPointers.size) {
        touchMap.classList.remove('map-dragging');
    }
}

for (const name of [
    'pointerup', 'pointercancel', 'lostpointercapture'
]) {
    touchMap.addEventListener(name, endMinimapPointer);
}

touchMap.addEventListener(
    'dblclick', () => setMinimapZoom(100)
);
'''


class Build(ast.NodeTransformer):
    def __init__(self, tree):
        self.files = False
        self.deps = False
        self.command = False
        self.launcher = False
        self.setup = False
        self.icon_copy = any(
            isinstance(item, ast.Call)
            and ast.unparse(item.func) == "shutil.copy2"
            and "icone.ico" in ast.unparse(item)
            for item in ast.walk(tree)
        )

    def visit_List(self, node):
        self.generic_visit(node)
        valores = [
            item.value for item in node.elts
            if isinstance(item, ast.Constant)
            and isinstance(item.value, str)
        ]

        if (
            "painel_jogadores.py" in valores
            and "mapa_overlay.py" in valores
        ):
            self.files = True
            if "central_replay.py" not in valores:
                node.elts.append(
                    ast.Constant("central_replay.py")
                )

        if "PyInstaller" in valores and "--add-data" in valores:
            self.command = True
            if "PIL" not in valores:
                node.elts.extend([
                    ast.Constant("--collect-all"),
                    ast.Constant("PIL"),
                ])

            if "--icon" not in valores:
                node.elts.extend(ast.parse(
                    '["--icon", fonte/"icone.ico", '
                    '"--add-data", '
                    'str(fonte/"icone.ico")+";."]',
                    mode="eval",
                ).body.elts)

        return node

    def visit_Expr(self, node):
        self.generic_visit(node)

        if (
            isinstance(node.value, ast.Call)
            and ast.unparse(node.value.func) == "shutil.copytree"
            and not self.icon_copy
        ):
            self.icon_copy = True
            return [
                node,
                ast.parse(
                    'shutil.copy2('
                    'projeto/"icone.ico", fonte/"icone.ico")'
                ).body[0],
            ]

        return node

    def visit_Constant(self, node):
        if not isinstance(node.value, str):
            return node

        texto = node.value

        if "mgz @" in texto and "pyinstaller==" in texto:
            self.deps = True
            if not re.search(
                r"(?im)^\s*pillow[<=>]", texto
            ):
                texto = texto.rstrip() + "\nPillow==11.3.0\n"

        if "import painel_jogadores as painel" in texto:
            self.launcher = True

            if "root.iconbitmap" not in texto:
                padrao = (
                    r"(?m)^([ \t]*)root\s*=\s*"
                    r"painel\.tk\.Tk\(\)[ \t]*$"
                )

                def inserir_icone(resultado):
                    espaco = resultado.group(1)
                    return (
                        resultado.group()
                        + "\n" + espaco
                        + "from caminhos_app import BUNDLE_DIR\n"
                        + espaco
                        + 'root.iconbitmap(default=str('
                        + 'BUNDLE_DIR / "icone.ico"))'
                    )

                texto, quantidade = re.subn(
                    padrao, inserir_icone, texto, count=1
                )
                if quantidade != 1:
                    raise RuntimeError(
                        "Inicialização do executável "
                        "não reconhecida."
                    )

        if "[Setup]" in texto and "[Run]" in texto:
            self.setup = True
            if "SetupIconFile=" not in texto:
                texto = texto.replace(
                    "[Setup]",
                    "[Setup]\nSetupIconFile=src\\icone.ico",
                    1,
                )

        return ast.copy_location(ast.Constant(texto), node)


class Timer(ast.NodeTransformer):
    def visit_Assign(self, node):
        self.generic_visit(node)

        alvo = any(
            isinstance(item, ast.Attribute)
            and isinstance(item.value, ast.Name)
            and item.value.id == "self"
            and item.attr == "next_frame"
            for item in node.targets
        )

        if alvo:
            value = node.value
            if (
                isinstance(value, ast.BinOp)
                and isinstance(value.op, ast.Add)
                and isinstance(value.left, ast.Name)
                and value.left.id == "now"
                and isinstance(value.right, ast.Constant)
                and value.right.value in (1, 5)
            ):
                value.right = ast.Constant(1)

        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            return ast.copy_location(
                ast.Constant(node.value.replace(
                    "Atualização-alvo: 5s.",
                    "Atualização-alvo: 1s.",
                )),
                node,
            )
        return node


def main():
    pasta = Path(__file__).resolve().parent

    obrigatorios = (
        "painel_jogadores.py",
        "painel_movel.py",
        "mapa_overlay.py",
        "gerar_instalador.py",
        "icone.png",
    )
    ausentes = [
        nome for nome in obrigatorios
        if not (pasta / nome).is_file()
    ]

    if ausentes:
        raise RuntimeError(
            "Arquivos ausentes: " + ", ".join(ausentes)
        )

    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise RuntimeError(
            "Execute primeiro:\n"
            "py -3.12 -m pip install Pillow==11.3.0"
        )

    alterados = {"central_replay.py": CENTRAL}

    texto = (pasta / "painel_jogadores.py").read_text(
        encoding="utf-8-sig"
    )

    if "_ativar_central_replay(globals())" not in texto:
        padrao = r"(?m)^from painel_movel import ativar.*$"
        integracao = (
            "from central_replay import ativar "
            "as _ativar_central_replay\n"
            "_ativar_central_replay(globals())\n\n"
        )

        texto, quantidade = re.subn(
            padrao,
            lambda resultado: integracao + resultado.group(),
            texto,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Não encontrei a integração móvel. "
                "Nenhum arquivo foi alterado."
            )

    alterados["painel_jogadores.py"] = texto

    arvore = ast.parse(
        (pasta / "painel_movel.py").read_text(
            encoding="utf-8-sig"
        )
    )
    encontrou_html = False

    for item in arvore.body:
        if not isinstance(item, ast.Assign):
            continue

        nomes = [
            alvo.id for alvo in item.targets
            if isinstance(alvo, ast.Name)
        ]

        if (
            "HTML" in nomes
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        ):
            html = item.value.value
            encontrou_html = True

            if "const minimapPointers" not in html:
                if (
                    "</style>" not in html
                    or "</script>" not in html
                ):
                    raise RuntimeError(
                        "Página móvel não reconhecida."
                    )

                css = (
                    "#viewport{touch-action:none;cursor:grab}"
                    "#viewport.map-dragging{cursor:grabbing}"
                    ".gesture-hint{font-size:12px;"
                    "color:#aabbaf;margin:8px 0 0}"
                )

                html = html.replace(
                    "</style>", css + "\n</style>", 1
                ).replace(
                    "</script>", PINCA + "\n</script>", 1
                )

                html = re.sub(
                    r"""<div\s+id=["']viewport["']\s*>""",
                    lambda resultado: (
                        '<p class="gesture-hint">'
                        "Pinça para ampliar · arraste para mover."
                        "</p>" + resultado.group()
                    ),
                    html,
                    count=1,
                )

            html = re.sub(
                r'(<span class="badge">)v[0-9.]+',
                r"\g<1>v0.2.0",
                html,
                count=1,
            )
            html = re.sub(
                r"setInterval\s*\(\s*update\s*,"
                r"\s*(?:5000|1000)\s*\)",
                "setInterval(update, 1000)",
                html,
            )
            html = html.replace(
                "Atualização-alvo: 5 segundos.",
                "Atualização-alvo: 1 segundo.",
            )
            item.value = ast.Constant(html)

        elif "VERSION" in nomes:
            item.value = ast.Constant("0.2.0")

    if not encontrou_html:
        raise RuntimeError("HTML móvel não encontrado.")

    ast.fix_missing_locations(arvore)
    alterados["painel_movel.py"] = (
        ast.unparse(arvore) + "\n"
    )

    arvore = Timer().visit(ast.parse(
        (pasta / "mapa_overlay.py").read_text(
            encoding="utf-8-sig"
        )
    ))
    ast.fix_missing_locations(arvore)
    alterados["mapa_overlay.py"] = (
        ast.unparse(arvore) + "\n"
    )

    arvore = ast.parse(
        (pasta / "gerar_instalador.py").read_text(
            encoding="utf-8-sig"
        )
    )
    adaptador = Build(arvore)
    arvore = adaptador.visit(arvore)

    if not all((
        adaptador.files,
        adaptador.deps,
        adaptador.command,
        adaptador.launcher,
        adaptador.setup,
        adaptador.icon_copy,
    )):
        raise RuntimeError(
            "Gerador diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)
    alterados["gerar_instalador.py"] = (
        ast.unparse(arvore) + "\n"
    )

    for nome, codigo in alterados.items():
        ast.parse(codigo, filename=nome)

    with Image.open(pasta / "icone.png") as original:
        figura = ImageOps.exif_transpose(
            original
        ).convert("RGBA")
        tamanho = max(figura.size)
        quadrado = Image.new(
            "RGBA", (tamanho, tamanho)
        )
        quadrado.alpha_composite(
            figura,
            (
                (tamanho - figura.width) // 2,
                (tamanho - figura.height) // 2,
            ),
        )

        icone = io.BytesIO()
        quadrado.save(
            icone,
            format="ICO",
            sizes=[
                (numero, numero)
                for numero in (
                    16, 20, 24, 32, 40, 48, 64, 128, 256
                )
            ],
        )

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for nome in list(alterados) + ["icone.ico"]:
        origem = pasta / nome
        if origem.exists():
            shutil.copy2(origem, backup / nome)

    for nome, codigo in alterados.items():
        (pasta / nome).write_text(
            codigo, encoding="utf-8"
        )

    (pasta / "icone.ico").write_bytes(icone.getvalue())

    print("\nCentral de replay, pinça e ícone preparados.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.2.0.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)