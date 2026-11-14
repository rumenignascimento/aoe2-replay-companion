"""Barra vertical de dados confirmados do jogador 2."""
import json
from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk

import minimapa_aoe2 as minimap


app = minimap.app


def confirmed_state(session):
    # O leitor atual fornece ordens, não confirmações da simulação.
    # None representa informação desconhecida.
    return {
        "player": 2,
        "game_ms": session.ms,
        "buildings_completed": None,
        "units_produced": None,
        "technologies_completed": None,
        "technologies_in_progress": None,
        "source": "replay_orders_only",
    }


def display_number(value):
    if (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
    ):
        return str(value)
    return "—"


def state_report(state):
    fields = (
        ("buildings_completed", "Construções concluídas"),
        ("units_produced", "Unidades produzidas"),
        ("technologies_completed", "Tecnologias concluídas"),
        ("technologies_in_progress", "Tecnologias em andamento"),
    )

    lines = [
        "JOGADOR 2 — SOMENTE DADOS CONFIRMADOS",
        f"Registros lidos até "
        f"{app.base.game_time(state['game_ms'])}",
        "",
    ]

    lines.extend(
        f"{name}: {display_number(state[key])}"
        for key, name in fields
    )

    lines.extend([
        "",
        "— = informação não confirmada pela fonte atual.",
        "Pedidos, quantidades iniciais e tempo decorrido "
        "não comprovam conclusão.",
        "Um pedido de pesquisa também não comprova "
        "que ela esteja em andamento.",
        "",
        "Ícones da barra:",
        "Castelo = construções.",
        "Pessoa = unidades.",
        "Engrenagem = tecnologias.",
        "✓ = concluído/produzido confirmado.",
        "Ampulheta = pesquisa em andamento confirmada.",
    ])

    return "\n".join(lines)


class BarQueue(app.ResultQueue):
    def get_nowait(self):
        result = super().get_nowait()
        epoch, kind, session, data = result

        if epoch == self.window.epoch and kind == "ok":
            self.window.bar_state = data["bar_state"]

        return result


class Window(app.Window):
    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)

        # Oculta os controles antigos da legenda.
        for widget in parent.winfo_children():
            if (
                isinstance(widget, ttk.LabelFrame)
                and str(widget.cget("text")).startswith("Legenda")
            ):
                widget.pack_forget()

        self.caption_corner.set("Superior esquerdo")
        self.caption_x.set("20")
        self.caption_y.set("80")

        self.bar_size = tk.IntVar(value=48)
        self.bar_opacity = tk.DoubleVar(value=1.0)

        panel = ttk.LabelFrame(
            parent,
            text="Barra vertical — jogador 2",
            padding=8,
        )
        panel.pack(
            fill="x", pady=6, before=self.report
        )

        ttk.Label(
            panel, text="Canto"
        ).grid(row=0, column=0)

        ttk.Combobox(
            panel,
            textvariable=self.caption_corner,
            values=(
                "Superior esquerdo",
                "Superior direito",
                "Inferior esquerdo",
                "Inferior direito",
            ),
            state="readonly",
            width=20,
        ).grid(row=0, column=1, padx=5)

        ttk.Label(
            panel, text="Margem X"
        ).grid(row=0, column=2)

        tk.Spinbox(
            panel,
            from_=0, to=10000, width=6,
            textvariable=self.caption_x,
        ).grid(row=0, column=3)

        ttk.Label(
            panel, text="Margem Y"
        ).grid(row=0, column=4)

        tk.Spinbox(
            panel,
            from_=0, to=10000, width=6,
            textvariable=self.caption_y,
        ).grid(row=0, column=5)

        ttk.Label(
            panel, text="Tamanho dos ícones"
        ).grid(row=1, column=0)

        tk.Spinbox(
            panel,
            from_=24, to=120,
            increment=4, width=6,
            textvariable=self.bar_size,
        ).grid(
            row=1, column=1,
            sticky="w", padx=5,
        )

        ttk.Checkbutton(
            panel,
            text="Exibir barra",
            variable=self.caption_show,
        ).grid(
            row=1, column=2, columnspan=2,
        )

        ttk.Label(
            panel, text="Opacidade"
        ).grid(row=2, column=0)

        ttk.Scale(
            panel,
            from_=.2, to=1,
            variable=self.bar_opacity,
        ).grid(row=2, column=1, sticky="ew")

        ttk.Label(
            panel,
            text=(
                "✓ confirmado · ampulheta: em andamento · "
                "— sem dados confirmados"
            ),
        ).grid(
            row=3, column=0, columnspan=6,
            sticky="w", pady=(6, 0),
        )

    def __init__(self, root, native):
        super().__init__(root, native)

        self.queue = BarQueue(self)
        self.bar_state = {}
        self.bar_cache = None

        root.title(
            "AoE2 — minimapa e barra de dados confirmados · J2"
        )

        for widget in self.report.master.winfo_children():
            if (
                isinstance(widget, ttk.Label)
                and str(widget.cget("text")).startswith(
                    "Relatório cumulativo"
                )
            ):
                widget.configure(
                    text="Dados confirmados do jogador 2"
                )

    def job(self, epoch, path, session, width):
        try:
            try:
                session = session or app.base.Session(path)
                session.poll()
            except (
                app.base.g.NotReady, PermissionError
            ) as exc:
                self.queue.put(
                    (epoch, "pending", session, str(exc))
                )
                return

            data = app.frame(
                session,
                app.base.ROOT / "mapas_atualizados",
                width,
            )

            state = confirmed_state(session)
            data["bar_state"] = state
            data["report"] = state_report(state)
            data["subtitle"] = data["report"]

            (
                Path(data["directory"])
                / "barra_confirmada.json"
            ).write_text(
                json.dumps(
                    state, ensure_ascii=False, indent=2
                ),
                "utf-8",
            )

            self.queue.put(
                (epoch, "ok", session, data)
            )

        except Exception as exc:
            self.queue.put(
                (epoch, "error", session, str(exc))
            )

    def draw_icon(self, kind, x, y, size, color):
        canvas = self.canvas

        def rect(a, b, d, e):
            canvas.create_rectangle(
                x + a * size,
                y + b * size,
                x + d * size,
                y + e * size,
                fill=color,
                outline="",
            )

        def line(points, width=.07):
            coords = []
            for a, b in points:
                coords.extend((
                    x + a * size,
                    y + b * size,
                ))

            canvas.create_line(
                *coords,
                fill=color,
                width=max(1, round(size * width)),
                joinstyle="round",
            )

        if kind == "building":
            for a in (.10, .40, .70):
                rect(a, .12, a + .20, .35)

            rect(.10, .30, .90, .88)

            canvas.create_rectangle(
                x + .40 * size,
                y + .56 * size,
                x + .60 * size,
                y + .88 * size,
                fill=app.KEY,
                outline="",
            )

        elif kind == "unit":
            canvas.create_oval(
                x + .32 * size,
                y + .10 * size,
                x + .68 * size,
                y + .46 * size,
                fill=color,
                outline="",
            )

            line([(.50, .48), (.50, .72)])
            line([(.23, .62), (.50, .50), (.77, .62)])
            line([(.27, .94), (.50, .72), (.73, .94)])

        elif kind == "tech":
            for a, b, d, e in (
                (.40, .05, .60, .28),
                (.40, .72, .60, .95),
                (.05, .40, .28, .60),
                (.72, .40, .95, .60),
            ):
                rect(a, b, d, e)

            canvas.create_oval(
                x + .20 * size,
                y + .20 * size,
                x + .80 * size,
                y + .80 * size,
                outline=color,
                width=max(2, round(size * .13)),
            )

        else:
            line(
                [
                    (.20, .12),
                    (.80, .12),
                    (.30, .88),
                    (.70, .88),
                    (.20, .12),
                ],
                .09,
            )
            line([(.20, .88), (.80, .88)], .09)

    def draw_bar(self, size):
        canvas = self.canvas
        canvas.delete("all")

        width = round(size * 3.5)
        pad = max(4, round(size * .12))
        row_height = round(size * 1.35)

        font = (
            "Segoe UI",
            max(12, round(size * .48)),
            "bold",
        )

        rows = (
            (
                "building",
                "buildings_completed",
                "#d5b47a",
            ),
            (
                "unit",
                "units_produced",
                "#80b4ff",
            ),
            (
                "tech",
                "technologies_completed",
                "#e7d980",
            ),
        )

        for index, (icon, key, color) in enumerate(rows):
            y = pad + index * row_height

            self.draw_icon(
                icon, pad, y, size, color
            )

            canvas.create_text(
                size * 1.38,
                y + size * .30,
                text="✓",
                fill="#8fd49a",
                font=(
                    "Segoe UI Symbol",
                    max(10, round(size * .25)),
                ),
                anchor="center",
            )

            canvas.create_text(
                size * 2.30,
                y + size * .30,
                text=display_number(
                    self.bar_state.get(key)
                ),
                fill="white",
                font=font,
            )

            if icon == "tech":
                self.draw_icon(
                    "hourglass",
                    size * 1.23,
                    y + size * .62,
                    size * .30,
                    "#e4c575",
                )

                canvas.create_text(
                    size * 2.30,
                    y + size * .85,
                    text=display_number(
                        self.bar_state.get(
                            "technologies_in_progress"
                        )
                    ),
                    fill="white",
                    font=font,
                )

            if index < 2:
                canvas.create_line(
                    pad,
                    y + row_height - 3,
                    width - pad,
                    y + row_height - 3,
                    fill="#8e8e8e",
                )

        height = pad * 2 + row_height * 3

        canvas.configure(
            width=width, height=height
        )
        self.caption_size = width, height

    def tick(self):
        # Mantém a atualização e o posicionamento do minimapa.
        app.base.Window.tick(self)

        if self.closing:
            return

        game = self.native.game()

        visible = (
            self.photo
            and self.caption_show.get()
            and (
                game
                or time.monotonic() < self.preview_until
            )
        )

        if not visible:
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
            max(1, int((h - 8) / 4.3)),
            max(1, int(w / 3.5)),
        )

        cache = (
            tuple(self.bar_state.items()),
            size,
        )

        if cache != self.bar_cache:
            self.draw_bar(size)
            self.bar_cache = cache

        try:
            self.caption.attributes(
                "-alpha",
                float(self.bar_opacity.get()),
            )
        except (ValueError, tk.TclError):
            pass

        iw, ih = self.caption_size
        mx = number(self.caption_x, 20, 0, 10000)
        my = number(self.caption_y, 80, 0, 10000)
        corner = self.caption_corner.get()

        dx = (
            w - iw - mx
            if corner in (
                "Superior direito",
                "Inferior direito",
            )
            else mx
        )
        dy = (
            h - ih - my
            if corner in (
                "Inferior esquerdo",
                "Inferior direito",
            )
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


if __name__ == "__main__":
    native = app.base.Native()
    root = tk.Tk()
    Window(root, native)
    root.mainloop()