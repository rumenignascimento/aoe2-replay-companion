import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


MODULO = r"""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
from pathlib import Path
import secrets
import socket
import threading
import time
from urllib.parse import urlsplit, parse_qs
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk

VERSION = "0.1.4"

HTML = r'''<!doctype html>
<html lang="pt-BR">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#101719">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>AoE2 · Companheiro</title>
<style>
:root {
    color-scheme: dark;
    font: 15px system-ui, sans-serif;
    background: #101719;
    color: #edf0ec;
}
* { box-sizing: border-box; }
body { margin: 0; }
header {
    padding: 20px 18px 12px;
    border-bottom: 1px solid #33403c;
    background: #15201f;
}
header small {
    color: #d8b870;
    letter-spacing: 3px;
    font-size: 11px;
}
h1 {
    font: 600 25px Georgia, serif;
    margin: 7px 0;
}
header p {
    color: #abbdb5;
    margin: 8px 0;
    font-size: 13px;
}
main {
    max-width: 1200px;
    margin: auto;
    padding: 14px;
}
section {
    background: #172321;
    border: 1px solid #34463e;
    border-radius: 16px;
    margin-bottom: 14px;
    padding: 14px;
}
label {
    font-size: 13px;
    color: #bdccc5;
}
select, button {
    font: inherit;
    color: inherit;
    background: #25342f;
    border: 1px solid #52634f;
    border-radius: 10px;
    padding: 10px;
    min-height: 44px;
}
select {
    flex: 1;
    min-width: 100px;
}
.tools {
    display: flex;
    align-items: center;
    gap: 12px;
}
.zoom {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 14px;
}
.zoom input {
    flex: 1;
    min-width: 0;
    accent-color: #d6b477;
}
#viewport {
    overflow: auto;
    max-height: 65vh;
    min-height: 130px;
    background: #101918;
    border-radius: 10px;
    margin-top: 14px;
}
#map {
    display: block;
    width: 100%;
    max-width: none;
    aspect-ratio: 2/1;
    object-fit: contain;
}
#status {
    font-size: 13px;
    color: #c2d7ca;
    min-height: 22px;
    margin: 12px 0 0;
}
h2 {
    font-size: 15px;
    margin: 0 0 12px;
}
h3 {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #d3b77e;
    margin: 15px 0 8px;
}
.cards {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(135px, 1fr));
    gap: 8px;
}
.card {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px;
    border-radius: 10px;
    background: #22332c;
    min-width: 0;
}
.card img {
    width: 40px;
    height: 40px;
    object-fit: contain;
    flex-shrink: 0;
}
.card div { min-width: 0; }
.card span {
    display: block;
    font-size: 12px;
    overflow-wrap: anywhere;
    color: #c9d6ce;
}
.card b { font-size: 20px; }
.empty {
    color: #a7bbb0;
    font-size: 13px;
}
.note {
    font-size: 12px;
    line-height: 1.6;
    color: #aabbaf;
    padding: 0 4px 24px;
}
.badge {
    border: 1px solid #5d6343;
    border-radius: 30px;
    padding: 3px 9px;
    font-size: 11px;
    color: #e6c987;
}
.heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}
.player {
    border-left: 3px solid var(--player, #c5a968);
}
@media(min-width: 850px) {
    main {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 16px;
        align-items: start;
    }
    .note { grid-column: 1/-1; }
    #details {
        max-height: 80vh;
        overflow: auto;
    }
}
</style>

<header>
    <small>SEGUNDA TELA · REDE LOCAL</small>
    <div class="heading">
        <h1>AoE2 · Companheiro</h1>
        <span class="badge">v0.1.4</span>
    </div>
    <p>O campo de batalha, na palma da mão.</p>
</header>

<main>
    <section>
        <div class="tools">
            <label for="player">Jogador</label>
            <select id="player">
                <option value="0">Todos</option>
            </select>
            <button id="refresh">Atualizar</button>
        </div>

        <div class="zoom">
            <label for="zoom">Zoom</label>
            <input id="zoom" type="range"
                   min="100" max="300" step="25" value="100">
            <output id="zoomValue">100%</output>
        </div>

        <div id="viewport">
            <img id="map" alt="Minimapa da partida" hidden>
        </div>

        <p id="status" role="status">Conectando ao computador…</p>
    </section>

    <div id="details">
        <section>
            <h2>Aguardando partida</h2>
            <p class="empty">
                Abra um replay ou inicie uma nova partida
                com o monitoramento ativo no PC.
            </p>
        </section>
    </div>

    <p class="note">
        Atualização-alvo: 5 segundos. Contadores representam
        pedidos registrados, não unidades vivas ou construções
        concluídas. Tecnologias indicam solicitações.
        Rotas mostram destinos solicitados, sem confirmar posições
        atuais. A seleção deste painel não altera a seleção do PC.
        Mantenha o computador ligado e conectado à mesma rede.
    </p>
</main>

<script>
let snapshot = null;
let revision = '';
let players = '';
let busy = false;
let force = true;

const select = document.getElementById('player');
const status = document.getElementById('status');
const image = document.getElementById('map');
const details = document.getElementById('details');

try {
    select.dataset.wanted =
        localStorage.getItem('aoe-player') || '0';
} catch (e) {}

function el(tag, text, cls) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
}

function group(parent, title, rows) {
    parent.append(el('h3', title));

    if (!rows.length) {
        parent.append(el(
            'p',
            'Nenhum pedido identificável registrado.',
            'empty'
        ));
        return;
    }

    const cards = el('div', undefined, 'cards');

    for (const row of rows) {
        const card = el('div', undefined, 'card');

        if (row.icon) {
            const icon = el('img');
            icon.src = row.icon;
            icon.alt = '';
            card.append(icon);
        }

        const text = el('div');
        text.append(
            el('span', row.name),
            el('b', String(row.count))
        );
        card.append(text);
        cards.append(card);
    }

    parent.append(cards);
}

function render() {
    if (!snapshot) return;

    details.replaceChildren();
    const chosen = Number(select.value);

    for (const player of snapshot.players) {
        if (chosen && player.player !== chosen) continue;

        const box = el('section', undefined, 'player');
        box.style.setProperty('--player', player.color);

        box.append(el(
            'h2',
            'Jogador ' + player.player + ' · pedidos'
        ));

        group(box, 'Construções', player.buildings);
        group(box, 'Produção militar', player.units);
        group(box, 'Tecnologias e avanços de era', player.techs);

        details.append(box);
    }

    if (!details.children.length) {
        details.append(el(
            'section', 'Sem dados para este jogador.'
        ));
    }

    image.hidden = false;
    image.src = 'map/' + chosen + '.svg?r=' +
                encodeURIComponent(revision);
}

function showAge() {
    if (!snapshot) return;

    const ago = Math.max(
        0,
        Math.floor(Date.now() / 1000 - snapshot.updated)
    );
    const seconds = Math.floor(snapshot.game_ms / 1000);

    status.textContent =
        'Partida ' +
        Math.floor(seconds / 60) + ':' +
        String(seconds % 60).padStart(2, '0') +
        ' · atualizado há ' + ago + 's' +
        (ago > 20 ? ' · aguardando novos dados do PC' : '');
}

async function update() {
    if (busy) return;
    busy = true;

    const controller = new AbortController();
    const timeout = setTimeout(
        () => controller.abort(), 8000
    );

    try {
        const query = force
            ? ''
            : '?r=' + encodeURIComponent(revision);

        const response = await fetch('state' + query, {
            cache: 'no-store',
            signal: controller.signal
        });

        if (response.status === 401) {
            status.textContent =
                'Conexão encerrada. Abra novamente ' +
                'o endereço exibido no PC.';
            return;
        }

        if (!response.ok) {
            throw Error('HTTP ' + response.status);
        }

        const data = await response.json();

        if (data.waiting) {
            status.textContent = data.message;
            return;
        }

        if (!data.unchanged) {
            snapshot = data;
            revision = data.revision;
            force = false;

            const ids = data.players
                .map(player => player.player).join(',');

            if (ids !== players) {
                const wanted =
                    select.dataset.wanted || select.value;

                players = ids;

                select.replaceChildren(
                    new Option('Todos', '0'),
                    ...data.players.map(player =>
                        new Option(
                            'Jogador ' + player.player,
                            String(player.player)
                        )
                    )
                );

                select.value = [...select.options].some(
                    option => option.value === wanted
                ) ? wanted : '0';

                select.dataset.wanted = '';
            }

            render();
        }

        showAge();

    } catch (error) {
        status.textContent =
            'Sem conexão com o PC. Confira o Wi-Fi ' +
            'e se o painel está ligado.';
    } finally {
        clearTimeout(timeout);
        busy = false;
    }
}

select.onchange = () => {
    try {
        localStorage.setItem('aoe-player', select.value);
    } catch (e) {}
    render();
};

document.getElementById('refresh').onclick = () => {
    force = true;
    update();
};

document.getElementById('zoom').oninput = event => {
    image.style.width = event.target.value + '%';
    document.getElementById('zoomValue').textContent =
        event.target.value + '%';
};

image.onerror = () => {
    status.textContent =
        'Mapa indisponível. Tentando atualizar…';
    force = true;
};

document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        force = true;
        update();
    }
});

setInterval(update, 5000);
update();
</script>
</html>'''


class Service:
    def __init__(self):
        self.lock = threading.Lock()
        self.server = None
        self.snapshot = None
        self.token = secrets.token_urlsafe(9)
        self.serial = 0
        self.window = None

    def start(self):
        if self.server:
            return

        service = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                path = urlsplit(self.path).path.split("/")

                if (
                    len(path) < 3
                    or not hmac.compare_digest(
                        path[1], service.token
                    )
                ):
                    return self.reply(
                        401,
                        b"Conexao nao autorizada.",
                        "text/plain",
                    )

                resource = "/".join(path[2:])

                if not resource:
                    return self.reply(
                        200,
                        HTML.encode(),
                        "text/html; charset=utf-8",
                    )

                with service.lock:
                    snap = service.snapshot

                if resource == "state":
                    if snap is None:
                        data = dict(
                            waiting=True,
                            message=(
                                "Aguardando leitura "
                                "da partida no PC…"
                            ),
                        )
                    else:
                        params = parse_qs(
                            urlsplit(self.path).query
                        )
                        if params.get("r") == [
                            snap["state"]["revision"]
                        ]:
                            data = dict(unchanged=True)
                        else:
                            data = snap["state"]

                    return self.reply(
                        200,
                        json.dumps(
                            data, ensure_ascii=False
                        ).encode(),
                        "application/json; charset=utf-8",
                    )

                if (
                    resource.startswith("map/")
                    and resource.endswith(".svg")
                ):
                    owner = resource[4:-4]
                    raw = (
                        snap["maps"].get(owner)
                        if snap else None
                    )
                    if raw:
                        return self.reply(
                            200,
                            raw.encode(),
                            "image/svg+xml; charset=utf-8",
                        )

                self.reply(
                    404, b"Indisponivel", "text/plain"
                )

            def reply(self, code, body, mime):
                self.send_response(code)
                self.send_header("Content-Type", mime)
                self.send_header(
                    "Content-Length", str(len(body))
                )
                self.send_header(
                    "Cache-Control", "no-store"
                )
                self.send_header(
                    "Referrer-Policy", "no-referrer"
                )
                self.send_header(
                    "X-Content-Type-Options", "nosniff"
                )
                self.end_headers()

                try:
                    self.wfile.write(body)
                except (ConnectionError, OSError):
                    pass

        server = None
        for port in range(8765, 8775):
            try:
                server = ThreadingHTTPServer(
                    ("0.0.0.0", port), Handler
                )
                break
            except OSError:
                continue

        if server is None:
            raise RuntimeError(
                "Portas 8765–8774 indisponíveis."
            )

        server.daemon_threads = True
        self.server = server

        threading.Thread(
            target=server.serve_forever,
            daemon=True,
        ).start()

    def stop(self):
        server, self.server = self.server, None

        with self.lock:
            self.snapshot = None

        if server:
            server.shutdown()
            server.server_close()

    def urls(self):
        addresses = set()

        try:
            with socket.socket(
                socket.AF_INET, socket.SOCK_DGRAM
            ) as sock:
                sock.connect(("192.0.2.1", 80))
                addresses.add(sock.getsockname()[0])
        except OSError:
            pass

        try:
            addresses.update(
                socket.gethostbyname_ex(
                    socket.gethostname()
                )[2]
            )
        except OSError:
            pass

        addresses = {
            address for address in addresses
            if not address.startswith(
                ("127.", "169.254.")
            )
        }

        return [
            f"http://{address}:"
            f"{self.server.server_port}/{self.token}/"
            for address in sorted(addresses)
        ]


def ativar(g):
    if g.get("_painel_movel_ativo"):
        return
    g["_painel_movel_ativo"] = True

    service = Service()
    g["MOBILE_SERVICE"] = service

    context = threading.local()
    old_frame = g["app"].frame
    render = g["app"].map_svg

    def icon(path):
        try:
            return (
                "data:image/png;base64,"
                + base64.b64encode(
                    Path(path).read_bytes()
                ).decode()
            )
        except (OSError, TypeError):
            return None

    def capture(session):
        old = getattr(
            g["CONTEXT"], "selection", None
        )

        try:
            g["CONTEXT"].selection = (0, 0)
            data = g["world_state"](session)
            players = []

            for player in data["per_player"]:
                buildings = []
                units = []
                techs = []

                for ident, count in player[
                    "building_counts"
                ].items():
                    record = g["p"].BUILDING_CATALOG.get(
                        int(ident)
                    )
                    if record and count > 0:
                        buildings.append(dict(
                            name=record[0],
                            count=count,
                            icon=icon(
                                g["t"].ROOT
                                / "icones_aoe2"
                                / f"building_{ident}.png"
                            ),
                        ))

                for ident, count in player[
                    "military_orders"
                ].items():
                    record = g["t"].ICONS.data.get(
                        int(ident)
                    )
                    if record and count > 0:
                        raw = g["t"].ICONS.images.get(
                            int(ident)
                        )
                        units.append(dict(
                            name=record["name"],
                            count=count,
                            icon=(
                                "data:image/png;base64,"
                                + base64.b64encode(raw).decode()
                                if raw else None
                            ),
                        ))

                for record in player["research_orders"]:
                    techs.append(dict(
                        name=record["name"],
                        count=record["requests"],
                        icon=icon(
                            g["m"].RESEARCH.paths.get(
                                ("tech", record["id"])
                            )
                        ),
                    ))

                players.append(dict(
                    player=player["player"],
                    color=player["color"],
                    buildings=buildings,
                    units=units,
                    techs=techs,
                ))

            maps = {}

            for owner in [0] + data["roster"]:
                g["CONTEXT"].selection = (owner, 0)
                svg = ET.fromstring(render(session))

                # O fundo usado pela transparência do
                # Windows não deve aparecer no celular.
                for node in svg.iter():
                    if node.get(
                        "fill", ""
                    ).lower() == "#ff00ff":
                        node.set("fill", "#101918")

                maps[str(owner)] = ET.tostring(
                    svg, encoding="unicode"
                )

            return dict(
                updated=time.time(),
                game_ms=session.ms,
                players=players,
                version=VERSION,
            ), maps

        finally:
            if old is None:
                try:
                    del g["CONTEXT"].selection
                except AttributeError:
                    pass
            else:
                g["CONTEXT"].selection = old

    def frame(session, *args, **kwargs):
        data = old_frame(session, *args, **kwargs)

        if service.server:
            try:
                state, maps = capture(session)
                window = service.window

                current = (
                    window is None
                    or getattr(
                        context, "epoch", window.epoch
                    ) == window.epoch
                )

                if service.server and current:
                    with service.lock:
                        service.serial += 1
                        state["revision"] = str(
                            service.serial
                        )
                        service.snapshot = dict(
                            state=state, maps=maps
                        )

            except Exception:
                logging.exception(
                    "Falha ao atualizar painel móvel"
                )

        return data

    g["app"].frame = frame
    Base = g["Window"]

    class Window(Base):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            service.window = self
            self.mobile_popup = None

            box = ttk.LabelFrame(
                self.report.master,
                text="Celular e tablet · rede local",
                padding=8,
            )
            box.pack(
                fill="x", pady=6, before=self.report
            )

            ttk.Button(
                box,
                text="Conectar celular / tablet…",
                command=self.mobile_dialog,
            ).pack(side="left")

            ttk.Label(
                box,
                text=(
                    "Minimapa e pedidos no navegador, "
                    "pela mesma rede."
                ),
            ).pack(side="left", padx=10)

        def attach(self, *args, **kwargs):
            with service.lock:
                service.snapshot = None

            return super().attach(*args, **kwargs)

        def job(self, *args, **kwargs):
            context.epoch = (
                args[0] if args
                else kwargs.get("epoch", self.epoch)
            )
            return super().job(*args, **kwargs)

        def mobile_dialog(self):
            if (
                self.mobile_popup
                and self.mobile_popup.winfo_exists()
            ):
                self.mobile_popup.lift()
                return

            top = tk.Toplevel(self.root)
            self.mobile_popup = top
            top.title("Conectar celular ou tablet")
            top.geometry("640x380")

            page = ttk.Frame(top, padding=16)
            page.pack(fill="both", expand=True)

            ttk.Label(
                page,
                text="Use a mesma rede do computador.",
                font=("Segoe UI", 12, "bold"),
            ).pack(anchor="w")

            ttk.Label(
                page,
                text=(
                    "Inicie o painel e abra um dos "
                    "endereços abaixo no celular.\n"
                    "Se o Windows pedir, permita "
                    "acesso em redes privadas."
                ),
                wraplength=580,
            ).pack(anchor="w", pady=10)

            text = tk.Text(
                page, height=6, wrap="word"
            )
            text.pack(fill="both", expand=True)

            def show(value):
                text.configure(state="normal")
                text.delete("1.0", "end")
                text.insert("1.0", value)
                text.configure(state="disabled")

            def start():
                try:
                    service.start()
                    urls = service.urls()

                    if urls:
                        show("\n\n".join(urls))
                    else:
                        show(
                            "Não identifiquei o IP local. "
                            "Execute ipconfig no Windows "
                            "e use:\n"
                            f"http://IP_DO_PC:"
                            f"{service.server.server_port}/"
                            f"{service.token}/"
                        )

                    self.next_frame = 0

                except Exception as error:
                    show(str(error))

            def stop():
                service.stop()
                show(
                    "Painel desligado. "
                    "As conexões foram encerradas."
                )

            def copiar():
                self.root.clipboard_clear()
                self.root.clipboard_append(
                    text.get("1.0", "end").strip()
                )

            row = ttk.Frame(page)
            row.pack(fill="x", pady=10)

            ttk.Button(
                row,
                text="Iniciar / mostrar endereço",
                command=start,
            ).pack(side="left")

            ttk.Button(
                row,
                text="Copiar endereços",
                command=copiar,
            ).pack(side="left", padx=6)

            ttk.Button(
                row,
                text="Desligar painel",
                command=stop,
            ).pack(side="left")

            ttk.Label(
                page,
                text=(
                    "O painel funciona enquanto este "
                    "programa estiver aberto.\n"
                    "O endereço de acesso muda ao "
                    "reiniciar o programa."
                ),
                wraplength=580,
            ).pack(anchor="w")

            if service.server:
                show("\n\n".join(service.urls()))
            else:
                show(
                    "Painel desligado. Clique em Iniciar."
                )

        def close(self):
            service.stop()
            super().close()

    g["Window"] = Window
"""


class Adaptar(ast.NodeTransformer):
    def __init__(self):
        self.encontrou = False

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
            self.encontrou = True
            if "painel_movel.py" not in valores:
                node.elts.append(
                    ast.Constant("painel_movel.py")
                )

        return node


def main():
    pasta = Path(__file__).resolve().parent
    painel = pasta / "painel_jogadores.py"
    gerador = pasta / "gerar_instalador.py"

    if not painel.is_file() or not gerador.is_file():
        raise RuntimeError(
            "Salve este script na pasta completa do projeto."
        )

    texto = painel.read_text(encoding="utf-8-sig")

    if "_ativar_painel_movel(globals())" not in texto:
        padrao = (
            r'''(?m)^if __name__\s*==\s*["']__main__["']\s*:'''
        )
        trecho = (
            "from painel_movel import ativar "
            "as _ativar_painel_movel\n"
            "_ativar_painel_movel(globals())\n\n"
        )

        texto, quantidade = re.subn(
            padrao,
            lambda resultado: trecho + resultado.group(),
            texto,
            count=1,
        )

        if quantidade != 1:
            raise RuntimeError(
                "Inicialização do painel não reconhecida. "
                "Nenhum arquivo foi alterado."
            )

    adaptador = Adaptar()
    arvore = adaptador.visit(ast.parse(
        gerador.read_text(encoding="utf-8-sig")
    ))

    if not adaptador.encontrou:
        raise RuntimeError(
            "Gerador diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)

    alterados = {
        "painel_jogadores.py": texto,
        "gerar_instalador.py": ast.unparse(arvore) + "\n",
        "painel_movel.py": MODULO.lstrip(),
    }

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

    print("\nPainel móvel adicionado ao projeto.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.1.4.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)