from collections import Counter
from datetime import datetime
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
import xml.etree.ElementTree as ET

import mapa_overlay as base


KEY = "#ff00ff"
NS = "http://www.w3.org/2000/svg"
CORNERS = (
    "Superior esquerdo",
    "Superior direito",
    "Inferior esquerdo",
    "Inferior direito",
)


# Renderiza sobre transparência real antes de aplicar a chave
# do Windows, evitando misturar roxo nas bordas dos recursos.
CLEAN_PIXELS = r"""
(async () => {
    await document.fonts.ready;

    const svg = document.querySelector('svg').cloneNode(true);
    const background = svg.querySelector('rect[fill="#ff00ff"]');
    if (background) background.remove();

    for (const node of svg.querySelectorAll('rect,circle,polygon,text')) {
        if (node.getAttribute('fill') !== 'none') {
            node.removeAttribute('stroke');
            node.removeAttribute('stroke-width');
            node.removeAttribute('paint-order');
        }
    }

    const image = new Image();
    const url = URL.createObjectURL(new Blob(
        [new XMLSerializer().serializeToString(svg)],
        {type: 'image/svg+xml;charset=utf-8'}
    ));

    try {
        await new Promise((resolve, reject) => {
            image.onload = resolve;
            image.onerror = reject;
            image.src = url;
        });

        const canvas = document.createElement('canvas');
        canvas.width = Number(svg.getAttribute('width'));
        canvas.height = Number(svg.getAttribute('height'));
        canvas.style.display = 'block';

        const ctx = canvas.getContext(
            '2d', {willReadFrequently: true}
        );
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

        const pixels = ctx.getImageData(
            0, 0, canvas.width, canvas.height
        );
        const d = pixels.data;

        for (let i = 0; i < d.length; i += 4) {
            if (d[i + 3] < 128) {
                d[i] = 255;
                d[i + 1] = 0;
                d[i + 2] = 255;
            }
            d[i + 3] = 255;
        }

        ctx.putImageData(pixels, 0, 0);
        document.body.replaceChildren(canvas);
        return true;
    } finally {
        URL.revokeObjectURL(url);
    }
})()
"""


def export_clean_png(svg, png):
    browser = base.g.find_browser()
    if not browser:
        raise RuntimeError(
            "Instale Microsoft Edge ou Google Chrome para gerar PNG."
        )

    import websocket

    image = ET.parse(svg).getroot()
    width = int(image.get("width"))
    height = int(image.get("height"))

    with tempfile.TemporaryDirectory(
        prefix="aoe2-mapa-", ignore_cleanup_errors=True
    ) as profile:
        command = [
            browser,
            "--headless",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--disable-background-networking",
            "--no-first-run",
            "--no-default-browser-check",
            f"--user-data-dir={profile}",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0",
            "about:blank",
        ]
        if sys.platform != "win32":
            command.insert(1, "--no-sandbox")

        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(
                subprocess, "CREATE_NO_WINDOW", 0
            ),
        )
        ws = None

        try:
            port_file = Path(profile) / "DevToolsActivePort"
            deadline = time.monotonic() + 20

            while not port_file.exists():
                if (
                    process.poll() is not None
                    or time.monotonic() > deadline
                ):
                    raise RuntimeError(
                        "Não foi possível abrir o navegador "
                        "para gerar a imagem."
                    )
                time.sleep(.1)

            port = int(port_file.read_text().splitlines()[0])
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({})
            )
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/json/new?about:blank",
                method="PUT",
            )
            with opener.open(request, timeout=5) as response:
                target = json.load(response)

            ws = websocket.create_connection(
                target["webSocketDebuggerUrl"],
                timeout=15,
                suppress_origin=True,
                http_no_proxy=["127.0.0.1", "localhost"],
            )
            sequence = 0

            def call(method, params=None):
                nonlocal sequence
                sequence += 1
                ws.send(json.dumps({
                    "id": sequence,
                    "method": method,
                    "params": params or {},
                }))

                while True:
                    answer = json.loads(ws.recv())
                    if answer.get("id") == sequence:
                        if "error" in answer:
                            raise RuntimeError(
                                "Falha na renderização do mapa."
                            )
                        return answer.get("result", {})

            call("Emulation.setDeviceMetricsOverride", {
                "width": width,
                "height": height,
                "deviceScaleFactor": 1,
                "mobile": False,
            })

            frame_id = call(
                "Page.getFrameTree"
            )["frameTree"]["frame"]["id"]

            content = (
                '<html><body style="margin:0;background:#ff00ff">'
                + Path(svg).read_text("utf-8")
                + "</body></html>"
            )
            call("Page.setDocumentContent", {
                "frameId": frame_id,
                "html": content,
            })

            result = call("Runtime.evaluate", {
                "expression": CLEAN_PIXELS,
                "awaitPromise": True,
                "returnByValue": True,
            })
            if result.get("exceptionDetails"):
                raise RuntimeError(
                    "Falha ao limpar as bordas do mapa."
                )

            screenshot = call("Page.captureScreenshot", {
                "format": "png",
                "captureBeyondViewport": False,
                "fromSurface": True,
            })
            data = base64.b64decode(screenshot["data"])

            if data[:8] != b"\x89PNG\r\n\x1a\n":
                raise RuntimeError("PNG inválido.")

            temporary = Path(str(png) + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(png)

        finally:
            if ws:
                try:
                    ws.send(json.dumps({
                        "id": 999999,
                        "method": "Browser.close",
                    }))
                    ws.close()
                except Exception:
                    pass

            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def map_svg(session):
    root = ET.Element(
        "{" + NS + "}svg",
        {
            "width": "900",
            "height": "900",
            "viewBox": "75 220 1120 1120",
        },
    )

    def add(tag, **attrs):
        return ET.SubElement(
            root,
            "{" + NS + "}" + tag,
            {k: str(v) for k, v in attrs.items()},
        )

    add(
        "rect", x=75, y=220,
        width=1120, height=1120, fill=KEY,
    )

    original = ET.fromstring(
        base.g.render_svg(session.model)
    )

    for child in list(original):
        if child.tag.rsplit("}", 1)[-1] != "g":
            continue

        for node in list(child):
            tag = node.tag.rsplit("}", 1)[-1]

            if (
                tag == "g"
                and node.get("shape-rendering") == "crispEdges"
            ):
                child.remove(node)
            elif (
                tag == "path"
                and node.get("stroke") == "#5a7053"
            ):
                child.remove(node)
            elif tag == "rect" and node.get("fill") == "none":
                child.remove(node)

        root.append(child)

    n = session.model["dimension"]

    def valid(x, y):
        return (
            isinstance(x, (int, float))
            and isinstance(y, (int, float))
            and 0 <= x < n
            and 0 <= y < n
        )

    def point(x, y):
        return 75 + x * 1120 / n, 220 + y * 1120 / n

    def color(owner):
        if isinstance(owner, int) and owner > 0:
            return base.PALETTE[
                (owner - 1) % len(base.PALETTE)
            ]
        return "#e9b361"

    for obj in session.initial:
        if (
            obj["type_id"] in base.g.TC_IDS
            or not valid(obj["x"], obj["y"])
        ):
            continue

        x, y = point(obj["x"], obj["y"])

        if obj["kind"] == "unit":
            add(
                "circle",
                cx=x, cy=y, r=6,
                fill=color(obj["owner"]),
            )
        else:
            add(
                "rect",
                x=x-7, y=y-7,
                width=14, height=14,
                fill=color(obj["owner"]),
            )

    for event in list(session.build_requests)[-80:]:
        if not valid(event.get("x"), event.get("y")):
            continue

        x, y = point(event["x"], event["y"])
        node = add(
            "rect",
            x=x-10, y=y-10,
            width=20, height=20,
            fill="none",
            stroke=color(event.get("player")),
            **{
                "stroke-width": 3,
                "stroke-dasharray": "4 3",
            },
        )
        title = ET.SubElement(node, "{" + NS + "}title")
        title.text = (
            "Pedido de construção; conclusão não confirmada."
        )

    return ET.tostring(root, encoding="unicode")


def player2_reports(session):
    research = [
        "JOGADOR 2 — PESQUISAS SOLICITADAS",
        "Conclusão não confirmada.",
        f"Eventos até {base.game_time(session.ms)}",
    ]

    requests = sorted(
        (
            e for e in session.research.values()
            if e.get("player") == 2
        ),
        key=lambda e: e["ms"],
    )

    for event in requests:
        research.append(
            f"{base.game_time(event['ms'])} | "
            f"{event['name']} | "
            f"{event['requests']} solicitação(ões); "
            "conclusão não confirmada"
        )

    if not requests:
        research.append(
            "Nenhuma solicitação encontrada para o jogador 2."
        )

    production = [
        "JOGADOR 2 — PRODUÇÃO SOLICITADA; "
        "CRIAÇÃO NÃO CONFIRMADA"
    ]

    events = [
        e for e in session.production_requests
        if e.get("player") == 2
    ]
    for event in events[-15:]:
        production.append(
            f"{base.game_time(event['ms'])} | "
            f"{event.get('name', 'Unidade não identificada')}"
        )

    return "\n".join(research), "\n".join(production)


def frame(session, directory, width):
    directory = Path(directory) / session.digest[:12]
    directory.mkdir(parents=True, exist_ok=True)

    image = ET.fromstring(map_svg(session))
    image.set("width", str(width))
    image.set("height", str(width))

    svg = directory / "overlay.svg"
    png = directory / "overlay.png"

    svg.write_text(
        ET.tostring(image, encoding="unicode"), "utf-8"
    )
    export_clean_png(svg, png)

    state = session.snapshot()
    state["rendered_at"] = datetime.now().isoformat(
        timespec="seconds"
    )

    research, production = player2_reports(session)
    report = research + "\n\n" + production

    (directory / "eventos.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        "utf-8",
    )
    (directory / "pesquisas.txt").write_text(
        research, "utf-8"
    )
    (directory / "producao.txt").write_text(
        production, "utf-8"
    )

    return {
        "png": png.read_bytes(),
        "state": state,
        "report": report,
        "directory": str(directory),
    }


def subtitle(session):
    lines = [
        f"JOGADOR 2 · registros até "
        f"{base.game_time(session.ms)}",
        "Estado inicial e pedidos; conclusões não confirmadas.",
    ]

    objects = [
        o for o in session.initial
        if o["owner"] == 2
    ]

    for kind, label in (
        ("unit", "Unidades iniciais"),
        ("building", "Construções iniciais"),
    ):
        counts = Counter(
            o["name"] for o in objects
            if o["kind"] == kind
        )
        detail = (
            ", ".join(
                f"{v} {k}" for k, v in counts.items()
            )
            or "nenhuma"
        )
        lines.append(f"{label}: {detail}")

    builds = sum(
        e.get("player") == 2
        for e in session.build_requests
    )
    production = sum(
        e.get("player") == 2
        for e in session.production_requests
    )
    lines.append(
        f"Pedidos no histórico disponível: "
        f"{builds} construção/muralha; "
        f"{production} produção."
    )

    recent = sorted(
        (
            e for e in session.research.values()
            if e.get("player") == 2
        ),
        key=lambda e: e["ms"],
        reverse=True,
    )

    lines.append(
        "Pesquisas solicitadas — conclusão não confirmada:"
    )

    for event in recent[:5]:
        name = (
            "Tear (Loom)"
            if event["name"] == "Loom"
            else event["name"]
        )
        lines.append(
            f"{base.game_time(event['ms'])} · {name}"
        )

    if not recent:
        lines.append(
            "Nenhuma solicitação encontrada para o jogador 2."
        )
    if len(recent) > 5:
        lines.append(
            f"+{len(recent)-5} no relatório completo."
        )

    lines.append(
        f"Quadro {datetime.now():%H:%M:%S} · "
        + (
            "fonte finalizada"
            if session.finished
            else "aguardando registros"
        )
    )

    return "\n".join(lines)


class ResultQueue(base.queue.Queue):
    def __init__(self, window):
        super().__init__()
        self.window = window

    def get_nowait(self):
        result = super().get_nowait()
        epoch, kind, session, data = result

        if epoch == self.window.epoch and kind == "ok":
            self.window.caption_text = data["subtitle"]

        return result


class Window(base.Window):
    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)

        self.caption_corner = tk.StringVar(
            value="Inferior esquerdo"
        )
        self.caption_x = tk.StringVar(value="20")
        self.caption_y = tk.StringVar(value="40")
        self.caption_width = tk.IntVar(value=680)
        self.caption_font = tk.IntVar(value=14)
        self.caption_show = tk.BooleanVar(value=True)

        panel = ttk.LabelFrame(
            parent,
            text="Legenda do jogador 2 — posição independente",
            padding=8,
        )
        panel.pack(
            fill="x", pady=6, before=self.report
        )

        ttk.Combobox(
            panel,
            textvariable=self.caption_corner,
            values=CORNERS,
            state="readonly",
            width=20,
        ).grid(row=0, column=0, padx=4)

        fields = (
            ("Margem X", self.caption_x),
            ("Margem Y", self.caption_y),
        )
        for col, (label, variable) in enumerate(fields, 1):
            ttk.Label(
                panel, text=label
            ).grid(row=0, column=col*2-1)

            tk.Spinbox(
                panel,
                from_=0, to=10000, width=6,
                textvariable=variable,
            ).grid(row=0, column=col*2)

        ttk.Checkbutton(
            panel,
            text="Exibir legenda",
            variable=self.caption_show,
        ).grid(row=1, column=0)

        ttk.Label(
            panel, text="Largura"
        ).grid(row=1, column=1)
        tk.Spinbox(
            panel,
            from_=300, to=1200, width=6,
            textvariable=self.caption_width,
        ).grid(row=1, column=2)

        ttk.Label(
            panel, text="Fonte"
        ).grid(row=1, column=3)
        tk.Spinbox(
            panel,
            from_=10, to=30, width=6,
            textvariable=self.caption_font,
        ).grid(row=1, column=4)

    def __init__(self, root, native):
        super().__init__(root, native)

        root.title(
            "AoE2 — mapa limpo + relatório do jogador 2"
        )
        root.geometry("920x900")

        self.overlay.configure(bg=KEY)
        self.overlay.attributes("-transparentcolor", KEY)
        self.image.configure(bg=KEY)

        self.caption = tk.Toplevel(root)
        self.caption.withdraw()
        self.caption.overrideredirect(True)
        self.caption.attributes("-topmost", True)
        self.caption.attributes("-transparentcolor", KEY)
        self.caption.configure(bg=KEY)

        self.canvas = tk.Canvas(
            self.caption,
            bg=KEY,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.caption.update_idletasks()

        self.caption_hwnd = native.u.GetAncestor(
            self.caption.winfo_id(), 2
        )
        native.u.SetWindowLongW(
            self.caption_hwnd,
            -20,
            native.u.GetWindowLongW(
                self.caption_hwnd, -20
            ) | 0x80800A0,
        )

        self.caption_cache = None
        self.caption_size = (680, 300)
        self.queue = ResultQueue(self)

    def target_width(self):
        try:
            width = min(
                900, max(300, int(self.width.get()))
            )
        except (ValueError, tk.TclError):
            width = 480

        game = self.native.game()
        if game:
            w, h = game[2:]
        else:
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()

        return max(1, min(width, w-40, h-40))

    def job(self, epoch, path, session, width):
        try:
            try:
                session = session or base.Session(path)
                session.poll()
            except (
                base.g.NotReady, PermissionError
            ) as exc:
                self.queue.put(
                    (epoch, "pending", session, str(exc))
                )
                return

            data = frame(
                session,
                base.ROOT / "mapas_atualizados",
                width,
            )
            data["subtitle"] = subtitle(session)

            self.queue.put(
                (epoch, "ok", session, data)
            )

        except Exception as exc:
            self.queue.put(
                (epoch, "error", session, str(exc))
            )

    def tick(self):
        super().tick()

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

        width = min(
            max(1, w),
            number(self.caption_width, 680, 300, 1200),
        )
        size = number(
            self.caption_font, 14, 10, 30
        )
        text = getattr(self, "caption_text", "")
        cache = text, width, size, h

        if cache != self.caption_cache:
            self.canvas.delete("all")

            self.canvas.create_text(
                8, 8,
                text=text,
                font=("Segoe UI", size, "bold"),
                fill="white",
                width=max(1, width-16),
                anchor="nw",
                justify="left",
            )

            bounds = self.canvas.bbox("all") or (
                0, 0, width, 30
            )
            height = min(
                max(1, h), bounds[3]+8
            )

            self.canvas.configure(
                width=width, height=height
            )
            self.caption_size = width, height
            self.caption_cache = cache

        iw, ih = self.caption_size
        mx = number(self.caption_x, 20, 0, 10000)
        my = number(self.caption_y, 40, 0, 10000)
        corner = self.caption_corner.get()

        dx = (
            w-iw-mx
            if corner in (CORNERS[1], CORNERS[3])
            else mx
        )
        dy = (
            h-ih-my
            if corner in (CORNERS[2], CORNERS[3])
            else my
        )

        ox = x + max(0, min(max(0, w-iw), dx))
        oy = y + max(0, min(max(0, h-ih), dy))

        self.caption.geometry(f"{iw}x{ih}")
        self.caption.update_idletasks()
        self.native.u.SetWindowPos(
            self.caption_hwnd, None,
            ox, oy, iw, ih, 0x14,
        )
        self.caption.deiconify()

    def close(self):
        self.caption.withdraw()
        super().close()


if __name__ == "__main__":
    native = base.Native()
    root = tk.Tk()
    Window(root, native)
    root.mainloop()