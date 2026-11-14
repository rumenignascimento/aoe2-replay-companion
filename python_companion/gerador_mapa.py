"""Gerador independente de mapas iniciais de AoE2 DE."""
import navegador_png_0422 as _png_backend_0422
import argparse
import base64
from collections import Counter
import hashlib
from html import escape
import io
import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
import zlib
ROOT = Path(__file__).resolve().parent
WIDTH, HEIGHT = (1800, 1480)
WOOD_IDS = {768, 2567, 2570, 399, 400, 401, 402, 403, 404, 405, 406, 407, 408, 409, 410, 411, 284, 413, 414, 1051, 1052, 1053, 1054, 1063, 2731, 2732, 302, 1717, 2580, 1984, 1347, 1348, 1349, 1350, 2583, 348, 349, 350, 351, 1248, 1249, 1250, 2016, 2017, 2025, 2027, 2028, 1144, 1146}
FRUIT_IDS = {59, 1059, 2650}
FISH_IDS = {53, 69, 450, 455, 456, 457, 458}
HUNT_IDS = {48, 65, 822, 1019, 1026, 1139, 1239, 1301, 1796, 2084, 2086, 2088}
HERD_IDS = {305, 594, 705, 833, 1142, 1243, 1245, 1596, 1598, 1600, 1963}
TC_IDS = {71, 109, 141, 142}
CATEGORIES = {'madeira': ('Madeira', '#2b6640', 'árvores e arbustos'), 'ouro': ('Ouro', '#f4ca49', 'blocos'), 'pedra': ('Pedra', '#bed5e6', 'blocos'), 'frutas': ('Frutas', '#c7447e', 'plantas'), 'caca': ('Caça', '#b67742', 'animais'), 'rebanho': ('Rebanho', '#fff3d4', 'animais'), 'peixes': ('Peixes', '#368fbe', 'pontos'), 'reliquias': ('Relíquias', '#b38ad2', 'unidades'), 'fazendas': ('Fazendas iniciais', '#b89058', 'unidades')}
PT = {'Arabia': 'Arábia', 'Japanese': 'Japoneses', 'Saracens': 'Sarracenos', 'Franks': 'Francos', 'Britons': 'Bretões', 'Huns': 'Hunos', 'Chinese': 'Chineses', 'Aztecs': 'Astecas', 'Vikings': 'Vikings', 'Teutons': 'Teutões', 'Mongols': 'Mongóis', 'Mayans': 'Maias'}

class NotReady(Exception):
    pass

class InvalidReplay(Exception):
    pass

def read_header(path):
    path = Path(path)
    with path.open('rb') as file:
        first = file.read(8)
        if len(first) < 8:
            raise NotReady('O jogo ainda está escrevendo o cabeçalho.')
        length, _ = struct.unpack('<II', first)
        if length == 0:
            raise NotReady('O jogo ainda não finalizou o cabeçalho.')
        if not 8 <= length <= 16 * 1024 * 1024:
            raise InvalidReplay('Formato ou tamanho não suportado.')
        rest = file.read(length - 8 + 4)
        if len(rest) != length - 8 + 4:
            raise NotReady('Cabeçalho incompleto. Aguardando o jogo.')
        file.seek(0)
        if file.read(8) != first:
            raise NotReady('Cabeçalho mudou durante a leitura.')
    prefix = first + rest
    try:
        stream = zlib.decompressobj(-15)
        data = stream.decompress(prefix[8:length], 64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024 or not stream.eof:
            raise InvalidReplay('Cabeçalho inválido ou muito grande.')
    except zlib.error as exc:
        raise InvalidReplay('Cabeçalho comprimido inválido.') from exc
    try:
        from mgz.fast.header import parse
        from mgz.reference import get_dataset
        from mgz.util import Version
        header = parse(io.BytesIO(prefix))
        if header['version'] is not Version.DE:
            raise InvalidReplay('Selecione uma gravação do AoE2 DE.')
        _, reference = get_dataset(header['version'], header.get('mod'))
    except ImportError as exc:
        raise InvalidReplay('Instale as dependências do projeto.') from exc
    except InvalidReplay:
        raise
    except Exception as exc:
        raise InvalidReplay('Leitor incompatível com este replay. Confira a versão com a correção 67+.') from exc
    digest = hashlib.sha256(prefix).hexdigest()
    return (header, reference, digest)

def category(ident, owner, name=''):
    if ident in TC_IDS and owner > 0:
        return 'centros'
    if ident in HERD_IDS:
        return 'rebanho'
    if ident == 50 and owner > 0:
        return 'fazendas'
    if owner != 0:
        return None
    if ident in WOOD_IDS or name.lower().startswith('tree ('):
        return 'madeira'
    if ident == 66:
        return 'ouro'
    if ident == 102:
        return 'pedra'
    if ident in FRUIT_IDS:
        return 'frutas'
    if ident in HUNT_IDS:
        return 'caca'
    if ident in FISH_IDS:
        return 'peixes'
    if ident == 285:
        return 'reliquias'
    return None

def extract(path):
    header, reference, digest = read_header(path)
    n = header['map']['dimension']
    if not isinstance(n, int) or not 16 <= n <= 512 or len(header['map']['tiles']) != n * n:
        raise InvalidReplay('Dimensões ou terreno inconsistentes.')
    de = header.get('de') or {}
    players = []
    for p in de.get('players', []):
        if p.get('number', 0) > 0 and p.get('type') in (2, 4):
            civ = reference['civilizations'].get(str(p['civilization_id']), {}).get('name')
            players.append({'slot': p['number'], 'civilization': civ, 'human': p['type'] == 2})
    points = []
    seen = set()
    for player in header['players']:
        owner = player['number']
        for obj in player['objects']:
            ident = obj['object_id']
            name = reference['objects'].get(str(ident), '')
            kind = category(ident, owner, name)
            if not kind:
                continue
            x = obj['position']['x']
            y = obj['position']['y']
            if not all((isinstance(v, (int, float)) and math.isfinite(v) and (0 <= v < n) for v in (x, y))):
                continue
            key = (kind, obj['instance_id'])
            if key in seen:
                continue
            seen.add(key)
            points.append({'kind': kind, 'id': ident, 'instance': obj['instance_id'], 'owner': owner, 'x': x, 'y': y})
    map_name = reference['maps'].get(str(de.get('rms_map_id'))) or 'Mapa personalizado'
    return {'schema': 1, 'source': Path(path).name, 'header_sha256': digest, 'build': de.get('build'), 'save_version': header.get('save_version'), 'map': map_name, 'dimension': n, 'players': players, 'tiles': [(t & 255, h) for t, h in header['map']['tiles']], 'points': points, 'counts': dict(Counter((p['kind'] for p in points))), 'snapshot': 'initial', 'restored_from_ms': header['map'].get('restore_time', 0), 'fog_of_war': False}

def clusters(points):
    groups = []
    left = set(range(len(points)))
    while left:
        group = [left.pop()]
        pending = group.copy()
        while pending:
            a = points[pending.pop()]
            neighbors = [i for i in left if math.hypot(a['x'] - points[i]['x'], a['y'] - points[i]['y']) <= 1.6]
            for i in neighbors:
                left.remove(i)
                group.append(i)
                pending.append(i)
        groups.append((len(group), sum((points[i]['x'] for i in group)) / len(group), sum((points[i]['y'] for i in group)) / len(group)))
    return groups

def render_svg(model):
    n = model['dimension']
    side = 1120
    left, top = (75, 220)
    scale = side / n
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">', '<rect width="1800" height="1480" fill="#101b24"/>', '<g font-family="Segoe UI, DejaVu Sans, Arial, sans-serif">']

    def text(x, y, value, size=17, color='#edf1ed', weight='normal', extra=''):
        out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" font-weight="{weight}" {extra}>{escape(str(value))}</text>')
    text(75, 65, 'AOE2 DE / GERADOR DE MAPAS', 16, '#91bda6', 'bold')
    text(75, 125, PT.get(model['map'], model['map']).upper(), 45, weight='bold')
    text(75, 165, f"{n} × {n} tiles  ·  {len(model['players'])} jogadores  ·  Build {model['build']}", 19, '#a7b4b4')
    snapshot = 'Estado da gravação retomada' if model.get('restored_from_ms') else 'Estado inicial reconstruído do replay'
    text(75, 190, snapshot + ' — mapa completo, sem névoa de guerra.', 16, '#a7b4b4')
    colors = {0: '#cfd7ac', 1: '#7caaba', 2: '#e5d6af', 17: '#9bb78a', 27: '#d6c9a5', 89: '#a9b98a', 128: '#c5cfa4'}
    out.append('<g shape-rendering="crispEdges">')
    for y in range(n):
        x = 0
        while x < n:
            terrain, height = model['tiles'][y * n + x]
            end = x + 1
            while end < n and model['tiles'][y * n + end] == (terrain, height):
                end += 1
            color = colors.get(terrain, '#cfd7ac')
            factor = max(0.85, min(1.1, 0.94 + height * 0.018))
            rgb = [min(255, int(int(color[i:i + 2], 16) * factor)) for i in (1, 3, 5)]
            color = '#' + ''.join((f'{c:02x}' for c in rgb))
            out.append(f'<rect x="{left + x * scale:.2f}" y="{top + y * scale:.2f}" width="{(end - x) * scale + 0.1:.2f}" height="{scale + 0.1:.2f}" fill="{color}"/>')
            x = end
    out.append('</g>')
    for t in range(0, n + 1, max(10, n // 6)):
        x = left + t * scale
        y = top + t * scale
        out.append(f'<path d="M{x:.2f} {top}V{top + side} M{left} {y:.2f}H{left + side}" stroke="#5a7053" stroke-opacity=".18"/>')
        text(x, top + side + 25, t, 12, '#a7b4b4', extra='text-anchor="middle"')
        text(left - 12, y + 4, t, 12, '#a7b4b4', extra='text-anchor="end"')
    for kind in list(CATEGORIES) + ['centros']:
        for point in (p for p in model['points'] if p['kind'] == kind):
            x = left + point['x'] * scale
            y = top + point['y'] * scale
            if kind == 'centros':
                color = ['#287ac5', '#c4544c', '#48a267', '#b492d0'][(point['owner'] - 1) % 4]
            else:
                color = CATEGORIES[kind][1]
            if kind == 'madeira':
                r = max(1.5, scale * 0.35)
                out.append(f'<rect x="{x - r:.2f}" y="{y - r:.2f}" width="{2 * r:.2f}" height="{2 * r:.2f}" fill="{color}"/>')
            elif kind == 'centros':
                out.append(f'<rect x="{x - 11:.2f}" y="{y - 11:.2f}" width="22" height="22" fill="{color}" stroke="white" stroke-width="2"/>')
                text(x, y + 5, point['owner'], 14, weight='bold', extra='text-anchor="middle"')
                player = next((p for p in model['players'] if p['slot'] == point['owner']), {})
                civ = player.get('civilization')
                label = f"J{point['owner']} · {PT.get(civ, civ or '?')}"
                tx = x + 15 if x < left + side * 0.7 else x - 15
                anchor = 'start' if tx > x else 'end'
                text(tx, y - 16, label, 16, '#10291c', 'bold', f'text-anchor="{anchor}" paint-order="stroke" stroke="#f2f4e6" stroke-width="4" stroke-linejoin="round"')
            elif kind in ('ouro', 'pedra', 'reliquias'):
                r = 6 if kind == 'reliquias' else 5
                shape = ' '.join((f'{x + math.cos(a) * r:.2f},{y + math.sin(a) * r:.2f}' for a in (math.pi / 2 + i * math.pi / 2 for i in range(4))))
                out.append(f'<polygon points="{shape}" fill="{color}" stroke="#3c4839" stroke-width=".8"/>')
            else:
                r = 3.5 if kind in ('caca', 'rebanho') else 4.5
                out.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{color}" stroke="#5a5143" stroke-width=".7"/>')
    for kind in ('ouro', 'pedra'):
        points = [p for p in model['points'] if p['kind'] == kind]
        for count, x, y in clusters(points):
            px = left + x * scale
            py = top + y * scale
            tx = px + 9 if x < n * 0.8 else px - 9
            anchor = 'start' if tx > px else 'end'
            text(tx, py + 21, f'{CATEGORIES[kind][0]} {count}', 13, '#293d2e', extra=f'text-anchor="{anchor}" paint-order="stroke" stroke="#f2f4e6" stroke-width="4" stroke-linejoin="round"')
    out.append(f'<rect x="{left}" y="{top}" width="{side}" height="{side}" fill="none" stroke="#6e8066"/>')
    text(1280, 250, 'RECURSOS', 25, weight='bold')
    text(1280, 280, 'Posições e quantidades iniciais', 15, '#a7b4b4')
    y = 345
    for kind, (title, color, unit) in CATEGORIES.items():
        count = model['counts'].get(kind, 0)
        if not count:
            continue
        out.append(f'<rect x="1280" y="{y - 16}" width="18" height="18" fill="{color}"/>')
        text(1320, y, title, 20, weight='bold')
        text(1320, y + 29, f'{count:,} {unit}'.replace(',', '.'), 16, '#a7b4b4')
        y += 88
    text(1280, y + 10, '■  Centro urbano inicial', 16)
    text(1280, y + 48, 'O número nas jazidas indica blocos.', 14, '#a7b4b4')
    text(75, 1400, 'MAPA COMPLETO · SEM NÉVOA DE GUERRA', 15, '#c6d0c8', 'bold')
    text(75, 1430, 'Esquema do início da partida; não representa recursos restantes nem alterações posteriores.', 14, '#a7b4b4')
    text(75, 1455, 'Fonte: ' + model['source'], 12, '#a7b4b4')
    out.append('</g></svg>')
    return '\n'.join(out)

def find_browser():
    for env in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        root = os.environ.get(env)
        if not root:
            continue
        for suffix in ('Microsoft/Edge/Application/msedge.exe', 'Google/Chrome/Application/chrome.exe'):
            candidate = Path(root) / suffix
            if candidate.is_file():
                return str(candidate)
    for name in ('msedge', 'chromium', 'chromium-browser', 'google-chrome'):
        path = shutil.which(name)
        if path:
            return path
    return None

def _export_png_once_0422(svg, png, browser):
    if not browser:
        raise RuntimeError('Para PNG, instale Microsoft Edge ou Google Chrome.')
    import websocket
    with tempfile.TemporaryDirectory(prefix='aoe2-mapa-', ignore_cleanup_errors=True) as profile:
        command = [browser, '--headless', '--disable-gpu', '--disable-dev-shm-usage', '--disable-background-networking', '--no-first-run', '--no-default-browser-check', f'--user-data-dir={profile}', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', 'about:blank']
        if sys.platform != 'win32':
            command.insert(1, '--no-sandbox')
        stderr_path = Path(profile) / 'browser-stderr.log'
        stream = stderr_path.open('wb')
        process = None
        success = False
        try:
            process = _png_backend_0422.launch(command, stream)
        except Exception:
            stream.close()
            _png_backend_0422.report_failure(browser, process, stderr_path)
            raise
        ws = None
        try:
            port_file = Path(profile) / 'DevToolsActivePort'
            deadline = time.monotonic() + 20
            while not port_file.exists():
                if process.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('Não foi possível abrir o navegador. SVG preservado.')
                time.sleep(0.1)
            port = int(port_file.read_text().splitlines()[0])
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            req = urllib.request.Request(f'http://127.0.0.1:{port}/json/new?about:blank', method='PUT')
            with opener.open(req, timeout=5) as response:
                target = json.load(response)
            ws = websocket.create_connection(target['webSocketDebuggerUrl'], timeout=15, suppress_origin=True, http_no_proxy=['127.0.0.1', 'localhost'])
            sequence = 0

            def call(method, params=None):
                nonlocal sequence
                sequence += 1
                ws.send(json.dumps({'id': sequence, 'method': method, 'params': params or {}}))
                while True:
                    answer = json.loads(ws.recv())
                    if answer.get('id') == sequence:
                        if 'error' in answer:
                            raise RuntimeError('Falha ao renderizar PNG.')
                        return answer.get('result', {})
            call('Emulation.setDeviceMetricsOverride', {'width': WIDTH, 'height': HEIGHT, 'deviceScaleFactor': 1, 'mobile': False})
            frame = call('Page.getFrameTree')['frameTree']['frame']['id']
            content = '<html><body style="margin:0;background:#101b24">' + Path(svg).read_text('utf-8') + '</body></html>'
            call('Page.setDocumentContent', {'frameId': frame, 'html': content})
            call('Runtime.evaluate', {'expression': 'document.fonts.ready.then(()=>true)', 'awaitPromise': True, 'returnByValue': True})
            result = call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': False, 'fromSurface': True})
            data = base64.b64decode(result['data'])
            if data[:8] != b'\x89PNG\r\n\x1a\n':
                raise RuntimeError('PNG inválido.')
            temporary = Path(str(png) + '.tmp')
            temporary.write_bytes(data)
            temporary.replace(png)
            success = True
        finally:
            try:
                if ws:
                    try:
                        ws.send(json.dumps({'id': 999999, 'method': 'Browser.close'}))
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
            finally:
                stream.close()
                if not success:
                    _png_backend_0422.report_failure(browser, process, stderr_path)

def export_png(svg, png):
    return _png_backend_0422.export_with_fallback(svg, png, find_browser, _export_png_once_0422)

def generate(replay, output, png=True):
    model = extract(replay)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    slug = re.sub('[^a-zA-Z0-9_-]+', '-', model['map']).strip('-') or 'mapa'
    stem = f"{slug}-{model['header_sha256'][:12]}"
    svg = output / (stem + '.svg')
    manifest = output / (stem + '.json')
    temporary = svg.with_suffix('.svg.tmp')
    temporary.write_text(render_svg(model), 'utf-8')
    temporary.replace(svg)
    manifest.write_text(json.dumps(model, ensure_ascii=False, indent=2), 'utf-8')
    image = output / (stem + '.png')
    warning = ''
    if png:
        try:
            export_png(svg, image)
        except Exception as exc:
            warning = 'PNG indisponível; SVG preservado. ' + str(exc)
    return {'svg': str(svg), 'png': str(image) if png and image.exists() and (not warning) else None, 'json': str(manifest), 'model': model, 'warning': warning}

def launch():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    class Window:

        def __init__(self, root):
            self.root = root
            self.busy = False
            self.paths = []
            self.pending = None
            self.baseline = set()
            self.last = None
            self.queue = queue.Queue()
            self.photo = None
            root.title('AoE2 — Gerador de mapas do replay')
            root.geometry('1080x800')
            self.folder = tk.StringVar()
            self.output = tk.StringVar(value=str(ROOT / 'mapas_gerados'))
            self.auto = tk.BooleanVar(value=False)
            self.png = tk.BooleanVar(value=True)
            self.status = tk.StringVar(value='Selecione a pasta savegame ou abra um replay.')
            frame = ttk.Frame(root, padding=16)
            frame.pack(fill='both', expand=True)
            ttk.Label(frame, text='Gerador de mapas · AoE2 DE', font=('Segoe UI', 22, 'bold')).pack(anchor='w')
            ttk.Label(frame, text='Mapa inicial completo, sem névoa de guerra. Aplicativo independente do treinador.').pack(anchor='w', pady=6)
            for label, var, command in [('Pasta savegame', self.folder, self.choose_folder), ('Pasta de imagens', self.output, self.choose_output)]:
                row = ttk.Frame(frame)
                row.pack(fill='x', pady=5)
                ttk.Label(row, text=label, width=18).pack(side='left')
                ttk.Entry(row, textvariable=var).pack(side='left', fill='x', expand=True)
                ttk.Button(row, text='Escolher…', command=command).pack(side='right', padx=6)
            ttk.Checkbutton(frame, text='Gerar automaticamente quando aparecer uma nova gravação', variable=self.auto, command=self.arm).pack(anchor='w', pady=5)
            ttk.Checkbutton(frame, text='Exportar PNG usando Edge/Chrome, além de SVG e JSON', variable=self.png).pack(anchor='w')
            self.files = tk.Listbox(frame, height=5, exportselection=False)
            self.files.pack(fill='x', pady=8)
            buttons = ttk.Frame(frame)
            buttons.pack(fill='x')
            for label, command in [('Abrir replay…', self.choose_file), ('Gerar selecionado', self.selected), ('Abrir imagem', self.open_image), ('Abrir pasta de imagens', self.open_output)]:
                ttk.Button(buttons, text=label, command=command).pack(side='left', padx=(0, 6))
            ttk.Label(frame, textvariable=self.status, wraplength=1020).pack(anchor='w', pady=10)
            self.preview = ttk.Label(frame, text='A prévia do PNG aparecerá aqui.')
            self.preview.pack(fill='both', expand=True)
            root.after(300, self.tick)

        def choose_folder(self):
            directory = filedialog.askdirectory(title='Selecione a pasta savegame')
            if directory:
                self.folder.set(directory)
                self.arm()
                self.refresh()

        def choose_output(self):
            directory = filedialog.askdirectory(title='Selecione onde salvar os mapas')
            if directory:
                self.output.set(directory)

        def arm(self):
            self.pending = None
            self.baseline = set(Path(self.folder.get()).glob('*.aoe2record')) if self.folder.get() else set()
            self.status.set('Monitorando novas gravações. As existentes podem ser geradas pela lista.')

        def choose_file(self):
            path = filedialog.askopenfilename(filetypes=[('Gravações AoE2 DE', '*.aoe2record')])
            if path:
                self.start(Path(path))

        def selected(self):
            selection = self.files.curselection()
            if selection:
                self.start(self.paths[selection[0]])
            else:
                messagebox.showinfo('Replay', 'Escolha uma gravação na lista ou use Abrir replay.')

        def start(self, path):
            if self.busy:
                return
            if not self.output.get().strip():
                messagebox.showinfo('Destino', 'Selecione uma pasta de imagens.')
                return
            self.busy = True
            self.pending = None
            self.last = None
            self.photo = None
            self.preview.config(image='', text='Gerando mapa…')
            self.status.set('Lendo cabeçalho e gerando mapa: ' + path.name)
            output = self.output.get()
            png = self.png.get()

            def worker():
                try:
                    result = generate(path, output, png)
                    self.queue.put(('ok', path, result))
                except (NotReady, PermissionError) as exc:
                    self.queue.put(('pending', path, str(exc)))
                except Exception as exc:
                    self.queue.put(('error', path, str(exc)))
            threading.Thread(target=worker, daemon=True).start()

        def refresh(self):
            if not self.folder.get():
                return
            try:
                paths = sorted(Path(self.folder.get()).glob('*.aoe2record'), key=lambda p: p.stat().st_mtime_ns, reverse=True)
            except OSError:
                return
            selection = self.files.curselection()
            selected = self.paths[selection[0]] if selection else None
            self.files.delete(0, 'end')
            self.paths = paths
            for i, path in enumerate(paths):
                self.files.insert('end', path.name)
                if path == selected:
                    self.files.selection_set(i)
            if self.auto.get() and (not self.busy) and (not self.pending):
                new = [p for p in paths if p not in self.baseline]
                if new:
                    self.start(new[0])

        def tick(self):
            while not self.queue.empty():
                kind, path, result = self.queue.get_nowait()
                self.busy = False
                if kind == 'pending':
                    self.pending = path
                    self.status.set(result + ' Tentando novamente em instantes.')
                elif kind == 'error':
                    self.baseline.add(path)
                    self.status.set('Não foi possível gerar: ' + result)
                else:
                    self.baseline.add(path)
                    self.last = result
                    model = result['model']
                    formats = 'PNG, SVG e dados disponíveis.' if result['png'] else 'SVG e dados disponíveis.'
                    self.status.set('Mapa gerado: ' + PT.get(model['map'], model['map']) + f" · {model['dimension']}" + f" × {model['dimension']}. " + (result['warning'] or formats))
                    if result['png']:
                        photo = tk.PhotoImage(file=result['png'])
                        factor = max(1, math.ceil(photo.width() / 960), math.ceil(photo.height() / 420))
                        self.photo = photo.subsample(factor, factor)
                        self.preview.config(image=self.photo, text='')
                    else:
                        self.preview.config(image='', text='SVG gerado. Use Abrir imagem para visualizar.')
            if self.pending and (not self.busy):
                self.start(self.pending)
            self.refresh()
            self.root.after(2000, self.tick)

        def open_image(self):
            if self.last:
                path = self.last['png'] or self.last['svg']
                webbrowser.open(Path(path).resolve().as_uri())

        def open_output(self):
            path = Path(self.output.get())
            path.mkdir(parents=True, exist_ok=True)
            if sys.platform == 'win32':
                os.startfile(str(path.resolve()))
            else:
                webbrowser.open(path.resolve().as_uri())
    root = tk.Tk()
    Window(root)
    root.mainloop()
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('replay', nargs='?')
    parser.add_argument('--saida', default=str(ROOT / 'mapas_gerados'))
    parser.add_argument('--sem-png', action='store_true')
    args = parser.parse_args()
    if args.replay:
        try:
            result = generate(args.replay, args.saida, not args.sem_png)
            print(json.dumps({key: value for key, value in result.items() if key != 'model'}, ensure_ascii=False, indent=2))
        except Exception as exc:
            parser.exit(1, str(exc) + '\n')
    else:
        launch()
