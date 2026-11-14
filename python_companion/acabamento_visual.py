
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageDraw, ImageTk
from central_replay import CARD, TEXT, BRONZE


def mix(a, b, fraction):
    return tuple(round(x + (y - x) * fraction) for x, y in zip(a, b))


def aplicar_tema(window):
    style = ttk.Style(window.root)
    images = []
    window._finish_images = images

    def photo(image):
        result = ImageTk.PhotoImage(image, master=window.root)
        images.append(result)
        return result

    def button(top, bottom, border, highlight, pressed=False):
        image = Image.new("RGBA", (32, 32))
        draw = ImageDraw.Draw(image)
        offset = 1 if pressed else 0
        end = 30 if pressed else 29

        draw.rectangle((1, end + 1, 30, 31), fill="#0c0f0d")

        a = tuple(bytes.fromhex(top.lstrip("#")))
        b = tuple(bytes.fromhex(bottom.lstrip("#")))

        for y in range(offset, end + 1):
            color = mix(a, b, (y - offset) / max(1, end - offset))
            draw.line((0, y, 31, y), fill=color)

        draw.rectangle((0, offset, 31, end), outline=border, width=1)
        draw.line((1, offset, 30, offset), fill=highlight, width=1)
        return photo(image)

    palettes = {
        "Iron": (
            "#373d36", "#252b27", "#77664c", "#998467",
            "#424a40", "#30372f", "#2e342e", "#252b25",
        ),
        "Primary": (
            "#d9b171", "#b68a4c", "#826033", "#f5d79e",
            "#e6c28a", "#c89c5a", "#c49756", "#a77a3c",
        ),
        "Test": (
            "#80603b", "#594227", "#a48150", "#c7a36d",
            "#87643b", "#654b2b", "#70512f", "#543c23",
        ),
    }

    for name, colors in palettes.items():
        a, b, border, highlight, ha, hb, pa, pb = colors
        normal = button(a, b, border, highlight)
        hover = button(ha, hb, border, highlight)
        pressed = button(pa, pb, border, border, True)
        disabled = button(
            "#3b3e37", "#2e332e", "#514d3f", "#696759"
        )

        element = "Finish." + name + ".surface"

        if element not in style.element_names():
            style.element_create(
                element, "image", normal,
                ("disabled", disabled),
                ("pressed", pressed),
                ("active", hover),
                border=(3, 3, 3, 5),
                sticky="nsew",
            )

        names = {
            "Iron": ("TButton", "Help.TButton"),
            "Primary": ("Primary.TButton", "Accent.TButton"),
            "Test": ("Test.TButton",),
        }[name]

        for target in names:
            style.layout(target, [
                (element, {
                    "sticky": "nswe",
                    "children": [
                        ("Button.focus", {
                            "sticky": "nswe",
                            "children": [
                                ("Button.padding", {
                                    "sticky": "nswe",
                                    "children": [
                                        ("Button.label", {"sticky": "nswe"})
                                    ],
                                })
                            ],
                        })
                    ],
                })
            ])

            foreground = (
                "#21190f" if name == "Primary"
                else "#fff0d8" if name == "Test"
                else TEXT
            )

            style.configure(
                target,
                foreground=foreground,
                background=CARD,
                padding=(14, 12, 14, 14),
                borderwidth=0,
                focuscolor=(
                    "#4a311a" if name == "Primary" else "#e7c58b"
                ),
                font=(
                    window.body_font,
                    10,
                    "bold" if name in ("Primary", "Test") else "normal",
                ),
            )

            style.map(
                target,
                padding=[("pressed", (14, 13, 14, 13))],
                foreground=[("disabled", "#a5a398")],
            )

    def tab(selected=False, hover=False):
        image = Image.new("RGBA", (32, 24))
        draw = ImageDraw.Draw(image)
        y = 0 if selected else 3

        fill = (
            CARD if selected
            else "#20251f" if hover
            else "#171c19"
        )

        draw.rectangle((0, y, 31, 23), fill=fill)
        draw.line((0, y + 1, 0, 23), fill="#6c5c44")
        draw.line((31, y + 1, 31, 23), fill="#6c5c44")
        draw.line(
            (0, y, 31, y),
            fill="#d4ab68" if selected else "#544c3c",
        )
        draw.line(
            (0, 23, 31, 23),
            fill=CARD if selected else "#66573f",
        )
        return photo(image)

    inactive = tab()
    active = tab(True)
    hover = tab(False, True)
    element = "Finish.Notebook.tab"

    if element not in style.element_names():
        style.element_create(
            element, "image", inactive,
            ("selected", active),
            ("active", hover),
            border=(3, 4, 3, 1),
            sticky="nsew",
        )

    style.layout("TNotebook.Tab", [
        (element, {
            "sticky": "nswe",
            "children": [
                ("Notebook.padding", {
                    "side": "top",
                    "sticky": "nswe",
                    "children": [
                        ("Notebook.focus", {
                            "side": "top",
                            "sticky": "nswe",
                            "children": [
                                ("Notebook.label", {
                                    "side": "top",
                                    "sticky": "",
                                })
                            ],
                        })
                    ],
                })
            ],
        })
    ])

    style.configure(
        "TNotebook.Tab",
        padding=(14, 9),
        foreground=TEXT,
        background=CARD,
        focuscolor=BRONZE,
        font=(window.body_font, 10),
    )
    style.map(
        "TNotebook.Tab",
        expand=[("selected", (0, 0, 0, 1))],
    )

    image = Image.new("RGBA", (20, 20), CARD)
    ImageDraw.Draw(image).rectangle(
        (0, 0, 19, 19), outline="#6c5c44", width=1
    )
    client = photo(image)
    element = "Finish.Notebook.client"

    if element not in style.element_names():
        style.element_create(
            element, "image", client,
            border=1, sticky="nsew",
        )

    style.layout("TNotebook", [
        (element, {"sticky": "nswe"})
    ])
    style.configure(
        "TNotebook",
        background=CARD,
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )


def atualizar_navegacao(window):
    states = getattr(window, "_finish_nav", None)
    if states is None:
        return

    for name, button in window.nav_buttons.items():
        active = name == window.central_nav

        button.configure(
            bg="#2a302b" if active else "#1e2221",
            fg=TEXT,
            activebackground="#2a302b" if active else "#2b322b",
            activeforeground=TEXT,
            relief="sunken" if active else "flat",
            borderwidth=1 if active else 0,
            highlightthickness=0,
            padx=17 if active else 18,
            pady=13 if active else 14,
        )

        stripe = states[name]
        if active:
            stripe.place(x=0, y=0, width=3, relheight=1)
        else:
            stripe.place_forget()


def preparar_navegacao(window):
    if getattr(window, "_finish_nav", None) is not None:
        atualizar_navegacao(window)
        return

    window._finish_nav = {}

    for name, button in window.nav_buttons.items():
        stripe = tk.Frame(button, bg="#be914f", borderwidth=0)
        stripe.bind(
            "<Button-1>",
            lambda event, b=button: b.invoke(),
        )
        window._finish_nav[name] = stripe

        def enter(event, n=name, b=button):
            if window.central_nav != n:
                b.configure(bg="#2b322b")

        def leave(event, n=name, b=button):
            if window.central_nav != n:
                b.configure(bg="#1e2221")

        button.bind("<Enter>", enter, add="+")
        button.bind("<Leave>", leave, add="+")

    atualizar_navegacao(window)
