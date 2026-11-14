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
VERSION = '0.2.2'
HTML = '<!doctype html>\n<html lang="pt-BR">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<meta name="theme-color" content="#101719">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<title>AoE2 · Companheiro</title>\n<style>\n:root {\n    color-scheme: dark;\n    font: 15px system-ui, sans-serif;\n    background: #101719;\n    color: #edf0ec;\n}\n* { box-sizing: border-box; }\nbody { margin: 0; }\nheader {\n    padding: 20px 18px 12px;\n    border-bottom: 1px solid #33403c;\n    background: #15201f;\n}\nheader small {\n    color: #d8b870;\n    letter-spacing: 3px;\n    font-size: 11px;\n}\nh1 {\n    font: 600 25px Georgia, serif;\n    margin: 7px 0;\n}\nheader p {\n    color: #abbdb5;\n    margin: 8px 0;\n    font-size: 13px;\n}\nmain {\n    max-width: 1200px;\n    margin: auto;\n    padding: 14px;\n}\nsection {\n    background: #172321;\n    border: 1px solid #34463e;\n    border-radius: 16px;\n    margin-bottom: 14px;\n    padding: 14px;\n}\nlabel {\n    font-size: 13px;\n    color: #bdccc5;\n}\nselect, button {\n    font: inherit;\n    color: inherit;\n    background: #25342f;\n    border: 1px solid #52634f;\n    border-radius: 10px;\n    padding: 10px;\n    min-height: 44px;\n}\nselect {\n    flex: 1;\n    min-width: 100px;\n}\n.tools {\n    display: flex;\n    align-items: center;\n    gap: 12px;\n}\n.zoom {\n    display: flex;\n    align-items: center;\n    gap: 10px;\n    margin-top: 14px;\n}\n.zoom input {\n    flex: 1;\n    min-width: 0;\n    accent-color: #d6b477;\n}\n#viewport {\n    overflow: auto;\n    max-height: 65vh;\n    min-height: 130px;\n    background: #101918;\n    border-radius: 10px;\n    margin-top: 14px;\n}\n#map {\n    display: block;\n    width: 100%;\n    max-width: none;\n    aspect-ratio: 2/1;\n    object-fit: contain;\n}\n#status {\n    font-size: 13px;\n    color: #c2d7ca;\n    min-height: 22px;\n    margin: 12px 0 0;\n}\nh2 {\n    font-size: 15px;\n    margin: 0 0 12px;\n}\nh3 {\n    font-size: 12px;\n    text-transform: uppercase;\n    letter-spacing: 1px;\n    color: #d3b77e;\n    margin: 15px 0 8px;\n}\n.cards {\n    display: grid;\n    grid-template-columns: repeat(auto-fill, minmax(135px, 1fr));\n    gap: 8px;\n}\n.card {\n    display: flex;\n    align-items: center;\n    gap: 9px;\n    padding: 10px;\n    border-radius: 10px;\n    background: #22332c;\n    min-width: 0;\n}\n.card img {\n    width: 40px;\n    height: 40px;\n    object-fit: contain;\n    flex-shrink: 0;\n}\n.card div { min-width: 0; }\n.card span {\n    display: block;\n    font-size: 12px;\n    overflow-wrap: anywhere;\n    color: #c9d6ce;\n}\n.card b { font-size: 20px; }\n.empty {\n    color: #a7bbb0;\n    font-size: 13px;\n}\n.note {\n    font-size: 12px;\n    line-height: 1.6;\n    color: #aabbaf;\n    padding: 0 4px 24px;\n}\n.badge {\n    border: 1px solid #5d6343;\n    border-radius: 30px;\n    padding: 3px 9px;\n    font-size: 11px;\n    color: #e6c987;\n}\n.heading {\n    display: flex;\n    align-items: center;\n    justify-content: space-between;\n    gap: 12px;\n}\n.player {\n    border-left: 3px solid var(--player, #c5a968);\n}\n@media(min-width: 850px) {\n    main {\n        display: grid;\n        grid-template-columns: 1.4fr 1fr;\n        gap: 16px;\n        align-items: start;\n    }\n    .note { grid-column: 1/-1; }\n    #details {\n        max-height: 80vh;\n        overflow: auto;\n    }\n}\n\n.fullscreen-controls {\n    display: flex;\n    justify-content: flex-end;\n    margin-top: 10px;\n}\n.fullscreen-controls button {\n    width: 100%;\n}\nbody.map-fullscreen-active {\n    overflow: hidden;\n}\n#mapPanel.map-expanded {\n    position: fixed;\n    inset: 0;\n    z-index: 9999;\n    display: flex;\n    flex-direction: column;\n    margin: 0;\n    border: 0;\n    border-radius: 0;\n    background: #101719;\n    height: 100vh;\n    height: 100dvh;\n    padding: 12px;\n    padding:\n        max(12px, env(safe-area-inset-top))\n        max(12px, env(safe-area-inset-right))\n        max(12px, env(safe-area-inset-bottom))\n        max(12px, env(safe-area-inset-left));\n}\n#mapPanel.map-expanded .tools,\n#mapPanel.map-expanded .zoom,\n#mapPanel.map-expanded .fullscreen-controls,\n#mapPanel.map-expanded #status {\n    flex-shrink: 0;\n}\n#mapPanel.map-expanded #viewport {\n    flex: 1;\n    min-height: 0;\n    max-height: none;\n    overscroll-behavior: contain;\n}\n\n#viewport{touch-action:none;cursor:grab}#viewport.map-dragging{cursor:grabbing}.gesture-hint{font-size:12px;color:#aabbaf;margin:8px 0 0}\n</style>\n\n<header>\n    <small>SEGUNDA TELA · REDE LOCAL</small>\n    <div class="heading">\n        <h1>AoE2 · Companheiro</h1>\n        <span class="badge">v0.2.2</span>\n    </div>\n    <p>O campo de batalha, na palma da mão.</p>\n</header>\n\n<main>\n    <section>\n        <div class="tools">\n            <label for="player">Jogador</label>\n            <select id="player">\n                <option value="0">Todos</option>\n            </select>\n            <button id="refresh">Atualizar</button>\n        </div>\n\n        <div class="fullscreen-controls"><button id="mapFullscreen" type="button" aria-pressed="false">Minimapa em tela cheia</button></div>\n<div class="zoom">\n            <label for="zoom">Zoom</label>\n            <input id="zoom" type="range"\n                   min="100" max="300" step="25" value="100">\n            <output id="zoomValue">100%</output>\n        </div>\n\n        <p class="gesture-hint">Pinça para ampliar · arraste para mover.</p><div id="viewport">\n            <img id="map" alt="Minimapa da partida" hidden>\n        </div>\n\n        <p id="status" role="status">Aguardando dados do computador…</p>\n    </section>\n\n    <div id="details">\n        <section>\n            <h2>Aguardando partida</h2>\n            <p class="empty">\n                Abra um replay ou inicie uma nova partida\n                com o monitoramento ativo no PC.\n            </p>\n        </section>\n    </div>\n\n    <p class="note">\n        Atualização contínua. Contadores representam\n        pedidos registrados, não unidades vivas ou construções\n        concluídas. Tecnologias indicam solicitações.\n        Rotas mostram destinos solicitados, sem confirmar posições\n        atuais. A seleção deste painel não altera a seleção do PC.\n        Mantenha o computador ligado e conectado à mesma rede.\n    </p>\n</main>\n\n<script>\nlet snapshot = null;\nlet revision = \'\';\nlet players = \'\';\nlet busy = false;\nlet force = true;\n\nconst select = document.getElementById(\'player\');\nconst status = document.getElementById(\'status\');\nconst image = document.getElementById(\'map\');\nconst details = document.getElementById(\'details\');\n\ntry {\n    select.dataset.wanted =\n        localStorage.getItem(\'aoe-player\') || \'0\';\n} catch (e) {}\n\nfunction el(tag, text, cls) {\n    const node = document.createElement(tag);\n    if (text !== undefined) node.textContent = text;\n    if (cls) node.className = cls;\n    return node;\n}\n\nfunction group(parent, title, rows) {\n    parent.append(el(\'h3\', title));\n\n    if (!rows.length) {\n        parent.append(el(\n            \'p\',\n            \'Nenhum pedido identificável registrado.\',\n            \'empty\'\n        ));\n        return;\n    }\n\n    const cards = el(\'div\', undefined, \'cards\');\n\n    for (const row of rows) {\n        const card = el(\'div\', undefined, \'card\');\n\n        if (row.icon) {\n            const icon = el(\'img\');\n            icon.src = row.icon;\n            icon.alt = \'\';\n            card.append(icon);\n        }\n\n        const text = el(\'div\');\n        text.append(\n            el(\'span\', row.name),\n            el(\'b\', String(row.count))\n        );\n        card.append(text);\n        cards.append(card);\n    }\n\n    parent.append(cards);\n}\n\nfunction render() {\n    if (!snapshot) return;\n\n    details.replaceChildren();\n    const chosen = Number(select.value);\n\n    for (const player of snapshot.players) {\n        if (chosen && player.player !== chosen) continue;\n\n        const box = el(\'section\', undefined, \'player\');\n        box.style.setProperty(\'--player\', player.color);\n\n        box.append(el(\n            \'h2\',\n            \'Jogador \' + player.player + \' · pedidos\'\n        ));\n\n        group(box, \'Construções\', player.buildings);\n        group(box, \'Produção militar\', player.units);\n        group(box, \'Tecnologias e avanços de era\', player.techs);\n\n        details.append(box);\n    }\n\n    if (!details.children.length) {\n        details.append(el(\n            \'section\', \'Sem dados para este jogador.\'\n        ));\n    }\n\n    image.hidden = false;\n    image.src = \'map/\' + chosen + \'.svg?r=\' +\n                encodeURIComponent(revision);\n}\n\nfunction showAge() {\n    if (!snapshot) return;\n\n    const ago = Math.max(\n        0,\n        Math.floor(Date.now() / 1000 - snapshot.updated)\n    );\n    const seconds = Math.floor(snapshot.game_ms / 1000);\n\n    status.textContent =\n        \'Partida \' +\n        Math.floor(seconds / 60) + \':\' +\n        String(seconds % 60).padStart(2, \'0\') +\n        \' · atualizado há \' + ago + \'s\' +\n        (ago > 20 ? \' · aguardando novos dados do PC\' : \'\');\n}\n\n\nlet continuousRetry = 0;\nlet continuousTimer;\n\nfunction scheduleContinuousUpdate() {\n    clearTimeout(continuousTimer);\n\n    if (!document.hidden) {\n        continuousTimer = setTimeout(\n            update,\n            continuousRetry\n                ? Math.min(10000, 500 * 2 ** continuousRetry)\n                : 0\n        );\n    }\n}\nasync function update() {\nclearTimeout(continuousTimer);\n    if (busy) return;\n    busy = true;\n\n    const controller = new AbortController();\n    const timeout = setTimeout(\n        () => controller.abort(), 25000\n    );\n\n    try {\n        const query = force\n            ? \'\'\n            : \'?r=\' + encodeURIComponent(revision);\n\n        const response = await fetch(\'state\' + query, {\n            cache: \'no-store\',\n            signal: controller.signal\n        });\n\n        if (response.status === 401) {continuousRetry = 6;\n            status.textContent =\n                \'Conexão encerrada. Abra novamente \' +\n                \'o endereço exibido no PC.\';\n            return;\n        }\n\n        if (!response.ok) {\n            throw Error(\'HTTP \' + response.status);\n        }\n\n        const data = await response.json();\ncontinuousRetry = 0;\n\n        if (data.waiting) {\n            status.textContent = data.message;\n            return;\n        }\n\n        if (!data.unchanged) {\n            snapshot = data;\n            revision = data.revision;\n            force = false;\n\n            const ids = data.players\n                .map(player => player.player).join(\',\');\n\n            if (ids !== players) {\n                const wanted =\n                    select.dataset.wanted || select.value;\n\n                players = ids;\n\n                select.replaceChildren(\n                    new Option(\'Todos\', \'0\'),\n                    ...data.players.map(player =>\n                        new Option(\n                            \'Jogador \' + player.player,\n                            String(player.player)\n                        )\n                    )\n                );\n\n                select.value = [...select.options].some(\n                    option => option.value === wanted\n                ) ? wanted : \'0\';\n\n                select.dataset.wanted = \'\';\n            }\n\n            render();\n        }\n\n        showAge();\n\n    } catch (error) {\n        continuousRetry = Math.min(6, continuousRetry + 1);\nstatus.textContent =\n            \'Sem conexão com o PC. Confira o Wi-Fi \' +\n            \'e se o painel está ligado.\';\n    } finally {\n        clearTimeout(timeout);\n        busy = false;\nscheduleContinuousUpdate();\n    }\n}\n\nselect.onchange = () => {\n    try {\n        localStorage.setItem(\'aoe-player\', select.value);\n    } catch (e) {}\n    render();\n};\n\ndocument.getElementById(\'refresh\').onclick = () => {\n    force = true;\n    update();\n};\n\ndocument.getElementById(\'zoom\').oninput = event => {\n    image.style.width = event.target.value + \'%\';\n    document.getElementById(\'zoomValue\').textContent =\n        event.target.value + \'%\';\n};\n\nimage.onerror = () => {\n    status.textContent =\n        \'Mapa indisponível. Tentando atualizar…\';\n    force = true;\n};\n\ndocument.addEventListener(\'visibilitychange\', () => {\n    if (!document.hidden) {\n        force = true;\n        update();\n    }\n});\n\n\nupdate();\n\nconst mapPanel = document.querySelector(\'main > section\');\nmapPanel.id = \'mapPanel\';\n\nconst fullscreenButton =\n    document.getElementById(\'mapFullscreen\');\n\nlet mapExpanded = false;\nlet nativeMapFullscreen = false;\nlet savedScroll = 0;\n\nfunction fullscreenElement() {\n    return document.fullscreenElement ||\n           document.webkitFullscreenElement;\n}\n\nfunction setMapExpanded(value) {\n    if (value && !mapExpanded) {\n        savedScroll = window.scrollY;\n    }\n\n    mapExpanded = value;\n    mapPanel.classList.toggle(\'map-expanded\', value);\n    document.body.classList.toggle(\n        \'map-fullscreen-active\', value\n    );\n\n    fullscreenButton.textContent = value\n        ? \'Sair da tela cheia\'\n        : \'Minimapa em tela cheia\';\n\n    fullscreenButton.setAttribute(\n        \'aria-pressed\', String(value)\n    );\n\n    if (!value) {\n        nativeMapFullscreen = false;\n        window.scrollTo(0, savedScroll);\n    }\n}\n\nasync function toggleMapFullscreen() {\n    if (mapExpanded) {\n        if (fullscreenElement() === mapPanel) {\n            const exit = document.exitFullscreen ||\n                         document.webkitExitFullscreen;\n\n            if (exit) {\n                try {\n                    await exit.call(document);\n                } catch (error) {\n                    return;\n                }\n            }\n        }\n\n        setMapExpanded(false);\n        return;\n    }\n\n    setMapExpanded(true);\n\n    const request = mapPanel.requestFullscreen ||\n                    mapPanel.webkitRequestFullscreen;\n\n    if (request) {\n        try {\n            await request.call(mapPanel);\n            nativeMapFullscreen =\n                fullscreenElement() === mapPanel;\n        } catch (error) {\n            nativeMapFullscreen = false;\n        }\n    }\n}\n\nfullscreenButton.addEventListener(\n    \'click\', toggleMapFullscreen\n);\n\nfunction syncMapFullscreen() {\n    if (fullscreenElement() === mapPanel) {\n        nativeMapFullscreen = true;\n    } else if (nativeMapFullscreen) {\n        setMapExpanded(false);\n    }\n}\n\ndocument.addEventListener(\n    \'fullscreenchange\', syncMapFullscreen\n);\ndocument.addEventListener(\n    \'webkitfullscreenchange\', syncMapFullscreen\n);\n\ndocument.addEventListener(\'keydown\', event => {\n    if (\n        event.key === \'Escape\' &&\n        mapExpanded &&\n        !nativeMapFullscreen\n    ) {\n        setMapExpanded(false);\n    }\n});\n\n\nconst touchMap = document.getElementById(\'viewport\');\nconst touchImage = document.getElementById(\'map\');\nconst touchSlider = document.getElementById(\'zoom\');\nconst touchOutput = document.getElementById(\'zoomValue\');\nconst minimapPointers = new Map();\n\nlet minimapGesture = null;\nlet minimapZoom = Number(touchSlider.value) || 100;\n\ntouchSlider.step = \'1\';\ntouchImage.draggable = false;\n\nfunction setMinimapZoom(value, center, anchor) {\n    const next = Math.min(\n        Number(touchSlider.max) || 300,\n        Math.max(\n            Number(touchSlider.min) || 100,\n            Math.round(value)\n        )\n    );\n\n    center = center || {\n        x: touchMap.clientWidth / 2,\n        y: touchMap.clientHeight / 2\n    };\n    anchor = anchor || {\n        x: (touchMap.scrollLeft + center.x) /\n           (minimapZoom / 100),\n        y: (touchMap.scrollTop + center.y) /\n           (minimapZoom / 100)\n    };\n\n    minimapZoom = next;\n    touchSlider.value = String(next);\n    touchImage.style.width = next + \'%\';\n    touchOutput.textContent = next + \'%\';\n\n    touchMap.scrollLeft =\n        anchor.x * (next / 100) - center.x;\n    touchMap.scrollTop =\n        anchor.y * (next / 100) - center.y;\n}\n\ntouchSlider.oninput = () =>\n    setMinimapZoom(Number(touchSlider.value));\n\nfunction beginMinimapGesture() {\n    const points = [...minimapPointers.values()];\n\n    if (points.length >= 2) {\n        const a = points[0], b = points[1];\n        const rect = touchMap.getBoundingClientRect();\n        const center = {\n            x: (a.x + b.x) / 2 - rect.left,\n            y: (a.y + b.y) / 2 - rect.top\n        };\n\n        minimapGesture = {\n            type: \'pinch\',\n            distance: Math.max(\n                1, Math.hypot(a.x-b.x, a.y-b.y)\n            ),\n            zoom: minimapZoom,\n            anchor: {\n                x: (touchMap.scrollLeft + center.x) /\n                   (minimapZoom / 100),\n                y: (touchMap.scrollTop + center.y) /\n                   (minimapZoom / 100)\n            }\n        };\n    } else if (points.length === 1) {\n        minimapGesture = {\n            type: \'pan\',\n            x: points[0].x,\n            y: points[0].y,\n            left: touchMap.scrollLeft,\n            top: touchMap.scrollTop\n        };\n    } else {\n        minimapGesture = null;\n    }\n}\n\ntouchMap.addEventListener(\'pointerdown\', event => {\n    if (\n        event.pointerType === \'mouse\' &&\n        event.button !== 0\n    ) return;\n\n    minimapPointers.set(event.pointerId, {\n        x: event.clientX, y: event.clientY\n    });\n\n    try {\n        touchMap.setPointerCapture(event.pointerId);\n    } catch (error) {}\n\n    touchMap.classList.add(\'map-dragging\');\n    beginMinimapGesture();\n    event.preventDefault();\n});\n\ntouchMap.addEventListener(\'pointermove\', event => {\n    if (!minimapPointers.has(event.pointerId)) return;\n\n    minimapPointers.set(event.pointerId, {\n        x: event.clientX, y: event.clientY\n    });\n\n    const points = [...minimapPointers.values()];\n\n    if (\n        points.length >= 2 &&\n        minimapGesture?.type === \'pinch\'\n    ) {\n        const a = points[0], b = points[1];\n        const rect = touchMap.getBoundingClientRect();\n\n        setMinimapZoom(\n            minimapGesture.zoom *\n            Math.hypot(a.x-b.x, a.y-b.y) /\n            minimapGesture.distance,\n            {\n                x: (a.x+b.x)/2 - rect.left,\n                y: (a.y+b.y)/2 - rect.top\n            },\n            minimapGesture.anchor\n        );\n    } else if (\n        points.length === 1 &&\n        minimapGesture?.type === \'pan\'\n    ) {\n        touchMap.scrollLeft =\n            minimapGesture.left -\n            (points[0].x - minimapGesture.x);\n\n        touchMap.scrollTop =\n            minimapGesture.top -\n            (points[0].y - minimapGesture.y);\n    }\n});\n\nfunction endMinimapPointer(event) {\n    minimapPointers.delete(event.pointerId);\n    beginMinimapGesture();\n\n    if (!minimapPointers.size) {\n        touchMap.classList.remove(\'map-dragging\');\n    }\n}\n\nfor (const name of [\n    \'pointerup\', \'pointercancel\', \'lostpointercapture\'\n]) {\n    touchMap.addEventListener(name, endMinimapPointer);\n}\n\ntouchMap.addEventListener(\n    \'dblclick\', () => setMinimapZoom(100)\n);\n\n</script>\n</html>'
from idiomas_app import traduzir_html, tr
HTML = traduzir_html(HTML)

class Service:

    def __init__(self):
        self.lock = threading.Condition(threading.RLock())
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
                path = urlsplit(self.path).path.split('/')
                if len(path) < 3 or not hmac.compare_digest(path[1], service.token):
                    return self.reply(401, b'Conexao nao autorizada.', 'text/plain')
                resource = '/'.join(path[2:])
                if not resource:
                    return self.reply(200, HTML.encode(), 'text/html; charset=utf-8')
                with service.lock:
                    if resource == 'state':
                        from urllib.parse import parse_qs
                        _continuous_requested = parse_qs(urlsplit(self.path).query).get('r', [''])[0]
                        if service.snapshot is None or service.snapshot['state']['revision'] == _continuous_requested:
                            service.lock.wait_for(lambda: service.server is None or (service.snapshot is not None and service.snapshot['state']['revision'] != _continuous_requested), timeout=20)
                    snap = service.snapshot
                if resource == 'state':
                    if snap is None:
                        data = dict(waiting=True, message=tr('Aguardando partida'))
                    else:
                        params = parse_qs(urlsplit(self.path).query)
                        if params.get('r') == [snap['state']['revision']]:
                            data = dict(unchanged=True)
                        else:
                            data = snap['state']
                    return self.reply(200, json.dumps(data, ensure_ascii=False).encode(), 'application/json; charset=utf-8')
                if resource.startswith('map/') and resource.endswith('.svg'):
                    owner = resource[4:-4]
                    raw = snap['maps'].get(owner) if snap else None
                    if raw:
                        return self.reply(200, raw.encode(), 'image/svg+xml; charset=utf-8')
                self.reply(404, b'Indisponivel', 'text/plain')

            def reply(self, code, body, mime):
                self.send_response(code)
                self.send_header('Content-Type', mime)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (ConnectionError, OSError):
                    pass
        server = None
        for port in range(8765, 8775):
            try:
                server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
                break
            except OSError:
                continue
        if server is None:
            raise RuntimeError('Portas 8765–8774 indisponíveis.')
        server.daemon_threads = True
        self.server = server
        threading.Thread(target=server.serve_forever, daemon=True).start()

    def stop(self):
        server, self.server = (self.server, None)
        with self.lock:
            self.snapshot = None
            self.lock.notify_all()
        if server:
            server.shutdown()
            server.server_close()

    def urls(self):
        addresses = set()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(('192.0.2.1', 80))
                addresses.add(sock.getsockname()[0])
        except OSError:
            pass
        try:
            addresses.update(socket.gethostbyname_ex(socket.gethostname())[2])
        except OSError:
            pass
        addresses = {address for address in addresses if not address.startswith(('127.', '169.254.'))}
        return [f'http://{address}:{self.server.server_port}/{self.token}/' for address in sorted(addresses)]

def ativar(g):
    if g.get('_painel_movel_ativo'):
        return
    g['_painel_movel_ativo'] = True
    service = Service()
    g['MOBILE_SERVICE'] = service
    context = threading.local()
    old_frame = g['app'].frame
    render = g['app'].map_svg

    def icon(path):
        try:
            return 'data:image/png;base64,' + base64.b64encode(Path(path).read_bytes()).decode()
        except (OSError, TypeError):
            return None

    def capture(session):
        old = getattr(g['CONTEXT'], 'selection', None)
        try:
            g['CONTEXT'].selection = (0, 0)
            data = g['world_state'](session)
            players = []
            for player in data['per_player']:
                buildings = []
                units = []
                techs = []
                for ident, count in player['building_counts'].items():
                    record = g['p'].BUILDING_CATALOG.get(int(ident))
                    if record and count > 0:
                        buildings.append(dict(name=record[0], count=count, icon=icon(g['t'].ROOT / 'icones_aoe2' / f'building_{ident}.png')))
                for ident, count in player['military_orders'].items():
                    record = g['t'].ICONS.data.get(int(ident))
                    if record and count > 0:
                        raw = g['t'].ICONS.images.get(int(ident))
                        units.append(dict(name=record['name'], count=count, icon='data:image/png;base64,' + base64.b64encode(raw).decode() if raw else None))
                for record in player['research_orders']:
                    techs.append(dict(name=record['name'], count=record['requests'], icon=icon(g['m'].RESEARCH.paths.get(('tech', record['id'])))))
                players.append(dict(player=player['player'], color=player['color'], buildings=buildings, units=units, techs=techs))
            maps = {}
            for owner in [0] + data['roster']:
                g['CONTEXT'].selection = (owner, 0)
                svg = ET.fromstring(render(session))
                for node in svg.iter():
                    if node.get('fill', '').lower() == '#ff00ff':
                        node.set('fill', '#101918')
                maps[str(owner)] = ET.tostring(svg, encoding='unicode')
            return (dict(updated=time.time(), game_ms=session.ms, players=players, version=VERSION), maps)
        finally:
            if old is None:
                try:
                    del g['CONTEXT'].selection
                except AttributeError:
                    pass
            else:
                g['CONTEXT'].selection = old

    def frame(session, *args, **kwargs):
        data = old_frame(session, *args, **kwargs)
        if service.server:
            try:
                state, maps = capture(session)
                window = service.window
                current = window is None or getattr(context, 'epoch', window.epoch) == window.epoch
                if service.server and current:
                    with service.lock:
                        service.serial += 1
                        state['revision'] = str(service.serial)
                        service.snapshot = dict(state=state, maps=maps)
                        service.lock.notify_all()
            except Exception:
                logging.exception('Falha ao atualizar painel móvel')
        return data
    g['app'].frame = frame
    Base = g['Window']

    class Window(Base):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            service.window = self
            self.mobile_popup = None
            box = ttk.LabelFrame(self.report.master, text='Celular e tablet · rede local', padding=8)
            box.pack(fill='x', pady=6, before=self.report)
            ttk.Button(box, text='Conectar celular / tablet…', command=self.mobile_dialog).pack(side='left')
            ttk.Label(box, text='Minimapa e pedidos no navegador, pela mesma rede.').pack(side='left', padx=10)
            menu_atual = self.root.cget('menu')
            if menu_atual:
                menu_principal = self.root.nametowidget(menu_atual)
            else:
                menu_principal = tk.Menu(self.root)
                self.root.configure(menu=menu_principal)
            menu_celular = tk.Menu(menu_principal, tearoff=False)
            menu_celular.add_command(label='Conectar celular / tablet…', command=self.mobile_dialog)
            menu_principal.add_cascade(label='Celular / tablet', menu=menu_celular)

        def attach(self, *args, **kwargs):
            with service.lock:
                service.snapshot = None
                service.lock.notify_all()
            return super().attach(*args, **kwargs)

        def job(self, *args, **kwargs):
            context.epoch = args[0] if args else kwargs.get('epoch', self.epoch)
            return super().job(*args, **kwargs)

        def mobile_dialog(self):
            if self.mobile_popup and self.mobile_popup.winfo_exists():
                self.mobile_popup.lift()
                return
            top = tk.Toplevel(self.root)
            self.mobile_popup = top
            top.title('Conectar celular ou tablet · QR Code')
            top.geometry(f'640x{min(680, top.winfo_screenheight() - 100)}')
            page = ttk.Frame(top, padding=16)
            page.pack(fill='both', expand=True)
            ttk.Label(page, text='Aponte a câmera do celular para o QR Code.', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
            ttk.Label(page, text='Use a mesma rede do computador. Se o Windows pedir,\npermita acesso em redes privadas.', wraplength=580).pack(anchor='w', pady=8)
            ttk.Label(page, text='Endereço de conexão:').pack(anchor='w')
            address = tk.StringVar(master=top)
            selector = ttk.Combobox(page, textvariable=address, state='readonly')
            selector.pack(fill='x', pady=6)
            qr_label = tk.Label(page, bg='white', borderwidth=12)
            qr_label.pack(pady=10)
            info = tk.StringVar(master=top, value='Painel desligado. Clique em Iniciar.')
            ttk.Label(page, textvariable=info, wraplength=580).pack(anchor='w', pady=6)

            def draw(event=None):
                url = address.get()
                if not url:
                    qr_label.configure(image='', text='QR Code indisponível')
                    top.qr_photo = None
                    return
                try:
                    import qrcode
                    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=1, border=4)
                    qr.add_data(url)
                    qr.make(fit=True)
                    matrix = qr.get_matrix()
                    size = len(matrix)
                    original = tk.PhotoImage(master=top, width=size, height=size)
                    pixels = ' '.join(('{' + ' '.join(('#000000' if cell else '#ffffff' for cell in row)) + '}' for row in matrix))
                    original.put(pixels)
                    scale = max(2, min(6, 280 // size))
                    top.qr_photo = original.zoom(scale, scale)
                    qr_label.configure(image=top.qr_photo, text='')
                    info.set('Escaneie o QR Code e abra o link.\nSe não conectar, selecione outro endereço acima.')
                except Exception as error:
                    qr_label.configure(image='', text='Não foi possível gerar o QR Code.')
                    top.qr_photo = None
                    info.set('O endereço continua disponível para copiar.\nDetalhes: ' + str(error))

            def start():
                try:
                    service.start()
                    urls = service.urls()
                    previous = address.get()
                    selector.configure(values=urls)
                    address.set(previous if previous in urls else urls[0] if urls else '')
                    draw()
                    if not urls:
                        info.set('Não identifiquei o IP local. Confira a conexão de rede do PC.')
                    self.next_frame = 0
                except Exception as error:
                    info.set(str(error))

            def stop():
                service.stop()
                selector.configure(values=[])
                address.set('')
                draw()
                info.set('Painel desligado. As conexões foram encerradas.')

            def copy_address():
                if address.get():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(address.get())
            selector.bind('<<ComboboxSelected>>', draw)
            buttons = ttk.Frame(page)
            buttons.pack(fill='x', pady=8)
            ttk.Button(buttons, text='Iniciar / atualizar QR', command=start).pack(side='left')
            ttk.Button(buttons, text='Copiar endereço', command=copy_address).pack(side='left', padx=8)
            ttk.Button(buttons, text='Desligar painel', command=stop).pack(side='left')
            ttk.Label(page, text='O programa precisa permanecer aberto no PC.\nAo reiniciá-lo, escaneie o novo QR Code.', wraplength=580).pack(anchor='w', pady=6)
            if service.server:
                start()
            else:
                draw()

        def close(self):
            service.stop()
            super().close()
    g['Window'] = Window
