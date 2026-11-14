from collections import Counter, deque
import base64
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime
import json
import math
import os
from pathlib import Path
import queue
import struct
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog
import xml.etree.ElementTree as ET
import gerador_mapa as g

class StrictFile:

    def __init__(self, handle, end):
        self.handle, self.end = (handle, end)

    def tell(self):
        return self.handle.tell()

    def read(self, length=-1):
        remaining = self.end - self.tell()
        if length < 0:
            length = remaining
        if length > remaining:
            raise EOFError
        value = self.handle.read(length)
        if len(value) != length:
            raise EOFError
        return value

    def seek(self, offset, whence=0):
        if whence == 0:
            target = offset
        elif whence == 1:
            target = self.tell() + offset
        else:
            target = self.end + offset
        if not 0 <= target <= self.end:
            raise EOFError
        return self.handle.seek(target)

def game_time(milliseconds):
    seconds = max(0, int(milliseconds) // 1000)
    return f'{seconds // 60:02}:{seconds % 60:02}'

class Session:

    def __init__(self, path):
        from mgz import fast
        self.fast = fast
        self.path = Path(path)
        self.header, self.reference, self.digest = g.read_header(path)
        self.model = g.extract(path)
        with self.path.open('rb') as handle:
            self.header_end = struct.unpack('<I', handle.read(4))[0] + 4
        self.offset = None
        self.ms = self.header['map'].get('restore_time', 0)
        self.recent = deque(maxlen=2000)
        self.research = {}
        self.build_requests = deque(maxlen=2000)
        self.production_requests = deque(maxlen=2000)
        self.order_totals = Counter()
        self.operations = 0
        self.unparsed = 0
        self.finished = False
        self.last_growth = time.monotonic()
        self.last_size = self.path.stat().st_size
        self.initial = []
        self.objects = {}
        annexes = {618, 619, 620, 1649, 890}
        for player in self.header['players']:
            if player['number'] <= 0:
                continue
            for obj in player['objects']:
                ident = obj['object_id']
                if obj['class_id'] not in (70, 80) or ident in annexes or ident in g.HERD_IDS:
                    continue
                p = obj['position']
                record = {'id': obj['instance_id'], 'owner': player['number'], 'type_id': ident, 'kind': 'unit' if obj['class_id'] == 70 else 'building', 'name': self.reference['objects'].get(str(ident)) or f'ID {ident}', 'x': p['x'], 'y': p['y'], 'status': 'initial_snapshot'}
                self.initial.append(record)
                self.objects[record['id']] = record

    def poll(self, max_operations=250000):
        size = self.path.stat().st_size
        if size < self.last_size or size < self.header_end:
            raise g.InvalidReplay('O arquivo foi truncado/substituído. Selecione a gravação novamente.')
        if size > self.last_size:
            self.last_growth = time.monotonic()
        self.last_size = size
        if self.finished:
            return 0
        with self.path.open('rb') as handle:
            bounded = StrictFile(handle, size)
            if self.offset is None:
                handle.seek(self.header_end)
                try:
                    self.fast.meta(bounded)
                except (EOFError, ValueError, struct.error):
                    return 0
                self.offset = handle.tell()
            handle.seek(self.offset)
            count = 0
            while handle.tell() < size and count < max_operations:
                start = handle.tell()
                try:
                    operation_id = struct.unpack('<I', bounded.read(4))[0]
                    if operation_id not in (1, 2, 3, 4, 6):
                        raise g.InvalidReplay(f'Operação {operation_id} não suportada na posição {start}.')
                    if operation_id == 1:
                        length = struct.unpack('<I', bounded.read(4))[0]
                        if not 1 <= length <= 1024 * 1024:
                            raise g.InvalidReplay('Comprimento de comando não suportado.')
                        if size - start < length + 12:
                            raise EOFError
                    handle.seek(start)
                    kind, value = self.fast.operation(bounded)
                except EOFError:
                    handle.seek(start)
                    break
                except (ValueError, IndexError, AssertionError, KeyError) as exc:
                    raise g.InvalidReplay(f'Comando não interpretado na posição {start}; leitura interrompida.') from exc
                if kind is self.fast.Operation.SYNC:
                    self.ms += value[0]
                elif kind is self.fast.Operation.ACTION:
                    action, payload = value
                    self.apply(action.name, payload)
                elif kind is self.fast.Operation.POSTGAME:
                    self.finished = True
                self.offset = handle.tell()
                self.operations += 1
                count += 1
            return count

    def apply(self, action, payload):
        if action == 'ERROR':
            self.unparsed += 1
            return
        supported = {'MOVE', 'ORDER', 'BUILD', 'WALL', 'RESEARCH', 'DE_QUEUE', 'QUEUE', 'MAKE', 'DELETE'}
        if action not in supported:
            return
        player = payload.get('player_id')
        ids = payload.get('object_ids', [])
        if player is None and ids and (ids[0] in self.objects):
            player = self.objects[ids[0]]['owner']
        record = {'ms': self.ms, 'action': action, 'player': player, 'status': 'command_recorded_not_completed', 'object_ids': list(ids), 'sequence': payload.get('sequence')}
        for key in ('x', 'y', 'x_end', 'y_end', 'building_id', 'technology_id', 'unit_id', 'amount'):
            if key in payload:
                record[key] = payload[key]
        if 'building_id' in record:
            record['name'] = self.reference['objects'].get(str(record['building_id'])) or f"Construção {record['building_id']}"
        if 'unit_id' in record:
            record['name'] = self.reference['objects'].get(str(record['unit_id'])) or f"Unidade {record['unit_id']}"
        if action == 'RESEARCH':
            technology = record.get('technology_id')
            record['name'] = self.reference['technologies'].get(str(technology)) or f'Tecnologia {technology}'
            key = (player, technology)
            old = self.research.get(key)
            self.research[key] = {**record, 'requests': old['requests'] + 1 if old else 1}
        if action in ('BUILD', 'WALL'):
            self.build_requests.append(record)
            self.order_totals['construction'] += 1
        if action in ('QUEUE', 'DE_QUEUE', 'MAKE'):
            self.production_requests.append(record)
            self.order_totals['production'] += 1
        self.recent.append(record)

    def snapshot(self):
        return {'schema': 2, 'source': self.path.name, 'header_sha256': self.digest, 'game_ms': self.ms, 'source_finished': self.finished, 'operations': self.operations, 'unparsed_actions': self.unparsed, 'initial_objects': self.initial, 'recent_orders': [e for e in self.recent if e['ms'] >= self.ms - 30000], 'research_requests': sorted(self.research.values(), key=lambda e: e['ms']), 'construction_orders': list(self.build_requests), 'production_orders': list(self.production_requests), 'order_totals': dict(self.order_totals), 'source_silent_seconds': round(time.monotonic() - self.last_growth, 1), 'meaning': 'Initial snapshot and recorded orders. Current positions, survivors and research completion are not confirmed.'}

    def research_report(self):
        lines = ['PESQUISAS SOLICITADAS — CONCLUSÃO NÃO CONFIRMADA', f'Arquivo: {self.path.name}', f'Eventos lidos até {game_time(self.ms)}', 'Uma solicitação não confirma início, conclusão ou ausência de cancelamento.', 'Pesquisas gratuitas/automáticas podem não gerar solicitação registrada.', '']
        for event in sorted(self.research.values(), key=lambda e: e['ms']):
            lines.append(f"{game_time(event['ms'])} | Jogador {event['player']} | {event['name']} | {event['requests']} solicitação(ões) | conclusão não confirmada")
        if not self.research:
            lines.append('Nenhuma solicitação de pesquisa encontrada no trecho disponível.')
        return '\n'.join(lines)

    def production_report(self):
        lines = ['PRODUÇÃO SOLICITADA — CRIAÇÃO NÃO CONFIRMADA']
        for event in list(self.production_requests)[-15:]:
            lines.append(f"{game_time(event['ms'])} | J{event['player']} | {event.get('name', 'Unidade não identificada')} | ordem registrada; produção não confirmada")
        return '\n'.join(lines)
ROOT = Path(__file__).resolve().parent
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
PALETTE = ['#287ac5', '#c4544c', '#48a267', '#b492d0']

def compact_svg(session):
    root = ET.Element('{' + NS + '}svg', {'width': '900', 'height': '1140', 'viewBox': '0 0 900 1140'})

    def add(parent, tag, **attrs):
        return ET.SubElement(parent, '{' + NS + '}' + tag, {k: str(v) for k, v in attrs.items()})

    def text(x, y, value, size=20, color='#edf1ed'):
        node = add(root, 'text', x=x, y=y, fill=color)
        node.set('font-family', 'Segoe UI, Arial, sans-serif')
        node.set('font-size', str(size))
        node.text = value
    add(root, 'rect', width=900, height=1140, fill='#101b24')
    map_name = g.PT.get(session.model['map'], session.model['map'])
    text(24, 31, f'{map_name} | inicial + ordens até {game_time(session.ms)}', 23)
    text(24, 55, 'Posições atuais e conclusões não confirmadas.', 18, '#e3c283')
    board = ET.fromstring(g.render_svg(session.model))
    board.attrib.update(x='24', y='72', width='852', height='852', viewBox='75 220 1120 1120')
    root.append(board)
    layer = add(board, 'g')
    n = session.model['dimension']
    scale = 1120 / n

    def coord(x, y):
        return (75 + x * scale, 220 + y * scale)

    def valid(x, y):
        return isinstance(x, (float, int)) and isinstance(y, (float, int)) and math.isfinite(x) and math.isfinite(y) and (0 <= x < n) and (0 <= y < n)
    for obj in session.initial:
        if obj['type_id'] in g.TC_IDS or not valid(obj['x'], obj['y']):
            continue
        x, y = coord(obj['x'], obj['y'])
        color = PALETTE[(obj['owner'] - 1) % len(PALETTE)]
        if obj['kind'] == 'unit':
            add(layer, 'circle', cx=x, cy=y, r=6, fill=color, stroke='white')
        else:
            add(layer, 'rect', x=x - 7, y=y - 7, width=14, height=14, fill=color, stroke='white')
    orders = list(session.build_requests)[-80:] + [e for e in session.snapshot()['recent_orders'] if e['action'] in ('MOVE', 'ORDER')][-40:]
    for event in orders:
        x, y = (event.get('x'), event.get('y'))
        if not valid(x, y):
            continue
        x, y = coord(x, y)
        owner = event.get('player')
        color = PALETTE[(owner - 1) % len(PALETTE)] if isinstance(owner, int) and owner > 0 else '#e9b361'
        if event['action'] in ('BUILD', 'WALL'):
            node = add(layer, 'rect', x=x - 10, y=y - 10, width=20, height=20, fill='none', stroke=color)
            node.set('stroke-width', '3')
            node.set('stroke-dasharray', '4 3')
        else:
            node = add(layer, 'path', d=f'M{x - 7} {y - 7}L{x + 7} {y + 7}M{x + 7} {y - 7}L{x - 7} {y + 7}', stroke=color)
            node.set('stroke-width', '3')
        title = add(node, 'title')
        title.text = f"Ordem {event['action']} — J{owner} — {game_time(event['ms'])}; execução não confirmada"
    text(24, 953, '● unidade inicial   ■ construção inicial   □ pedido   × destino (30s)', 18)
    counts = Counter((o['kind'] for o in session.initial))
    text(24, 980, f"Inicial: {counts['unit']} unidades / {counts['building']} construções | pedidos de produção: {session.order_totals['production']}", 17, '#a7b4b4')
    text(24, 1012, 'PESQUISAS SOLICITADAS — conclusão não confirmada', 20, '#e3c283')
    requests = sorted(session.research.values(), key=lambda e: e['ms'], reverse=True)
    for index, event in enumerate(requests[:3]):
        name = 'Tear (Loom)' if event['name'] == 'Loom' else event['name']
        text(24, 1043 + index * 25, f"{game_time(event['ms'])} | J{event['player']} | {name[:52]}", 19)
    if not requests:
        text(24, 1043, 'Nenhuma solicitação encontrada no trecho disponível.', 18, '#a7b4b4')
    if len(requests) > 3:
        footer = f'+{len(requests) - 3} no relatório completo | quadro {datetime.now():%H:%M:%S}'
    else:
        source = 'finalizada' if session.finished else 'até ' + game_time(session.ms)
        footer = f'Quadro {datetime.now():%H:%M:%S} | fonte {source}'
    text(24, 1118, footer, 16, '#a7b4b4')
    return ET.tostring(root, encoding='unicode')

def frame(session, directory, width):
    directory = Path(directory) / session.digest[:12]
    directory.mkdir(parents=True, exist_ok=True)
    height = math.ceil(width * 1140 / 900)
    image = ET.fromstring(compact_svg(session))
    image.set('width', str(width))
    image.set('height', str(height))
    svg_path = directory / 'overlay.svg'
    png_path = directory / 'overlay.png'
    svg_path.write_text(ET.tostring(image, encoding='unicode'), 'utf-8')
    old_width, old_height = (g.WIDTH, g.HEIGHT)
    try:
        g.WIDTH, g.HEIGHT = (width, height)
        g.export_png(svg_path, png_path)
    finally:
        g.WIDTH, g.HEIGHT = (old_width, old_height)
    state = session.snapshot()
    state['rendered_at'] = datetime.now().isoformat(timespec='seconds')
    (directory / 'eventos.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), 'utf-8')
    report = session.research_report()
    production = session.production_report()
    (directory / 'pesquisas.txt').write_text(report, 'utf-8')
    (directory / 'producao.txt').write_text(production, 'utf-8')
    return {'png': png_path.read_bytes(), 'state': state, 'report': report + '\n\n' + production, 'directory': str(directory)}

class Native:

    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('O overlay requer Windows.')
        self.u = C.WinDLL('user32')
        self.k = C.WinDLL('kernel32')
        specs = [(self.u, 'GetForegroundWindow', [], W.HWND), (self.u, 'GetAncestor', [W.HWND, W.UINT], W.HWND), (self.u, 'GetWindowThreadProcessId', [W.HWND, C.POINTER(W.DWORD)], W.DWORD), (self.u, 'GetClientRect', [W.HWND, C.POINTER(W.RECT)], W.BOOL), (self.u, 'ClientToScreen', [W.HWND, C.POINTER(W.POINT)], W.BOOL), (self.u, 'GetWindowLongW', [W.HWND, C.c_int], C.c_long), (self.u, 'SetWindowLongW', [W.HWND, C.c_int, C.c_long], C.c_long), (self.u, 'SetWindowPos', [W.HWND, W.HWND, C.c_int, C.c_int, C.c_int, C.c_int, W.UINT], W.BOOL), (self.u, 'RegisterHotKey', [W.HWND, C.c_int, W.UINT, W.UINT], W.BOOL), (self.u, 'UnregisterHotKey', [W.HWND, C.c_int], W.BOOL), (self.u, 'PeekMessageW', [C.POINTER(W.MSG), W.HWND, W.UINT, W.UINT, W.UINT], W.BOOL), (self.k, 'OpenProcess', [W.DWORD, W.BOOL, W.DWORD], W.HANDLE), (self.k, 'QueryFullProcessImageNameW', [W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD)], W.BOOL), (self.k, 'CloseHandle', [W.HANDLE], W.BOOL)]
        for library, name, args, result in specs:
            fn = getattr(library, name)
            fn.argtypes = args
            fn.restype = result
        try:
            self.u.SetProcessDpiAwarenessContext(C.c_void_p(-4))
        except AttributeError:
            self.u.SetProcessDPIAware()

    def game(self):
        hwnd = self.u.GetForegroundWindow()
        pid = W.DWORD()
        self.u.GetWindowThreadProcessId(hwnd, C.byref(pid))
        handle = self.k.OpenProcess(4096, False, pid.value)
        if not handle:
            return None
        try:
            name = C.create_unicode_buffer(32768)
            length = W.DWORD(32768)
            if not self.k.QueryFullProcessImageNameW(handle, 0, name, C.byref(length)):
                return None
            if Path(name.value).name.lower() != 'aoe2de_s.exe':
                return None
        finally:
            self.k.CloseHandle(handle)
        rect, point = (W.RECT(), W.POINT())
        if not self.u.GetClientRect(hwnd, C.byref(rect)):
            return None
        if not self.u.ClientToScreen(hwnd, C.byref(point)):
            return None
        return (point.x, point.y, rect.right, rect.bottom)

class Window:

    def __init__(self, root, native):
        self.root, self.native = (root, native)
        self.path = None
        self.session = None
        self.pending = None
        self.busy = False
        self.epoch = 0
        self.next_frame = 0
        self.last_scan = 0
        self.baseline = set()
        self.queue = queue.Queue()
        self.closing = False
        self.photo = None
        self.last_directory = None
        self.preview_until = 0
        root.title('AoE2 — Mapa em overlay · inicial + ordens')
        root.geometry('850x760')
        self.folder = tk.StringVar()
        self.width = tk.IntVar(value=480)
        self.opacity = tk.DoubleVar(value=0.85)
        self.show = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value='Selecione a pasta savegame antes de iniciar uma nova partida.')
        page = ttk.Frame(root, padding=16)
        page.pack(fill='both', expand=True)
        ttk.Label(page, text='Mapa inicial + ordens do replay', font=('Segoe UI', 20, 'bold')).pack(anchor='w')
        ttk.Label(page, text='Atualização contínua. Ordens não confirmam posições atuais nem conclusões.', wraplength=800).pack(anchor='w', pady=6)
        row = ttk.Frame(page)
        row.pack(fill='x', pady=8)
        ttk.Entry(row, textvariable=self.folder, state='readonly').pack(side='left', fill='x', expand=True)
        ttk.Button(row, text='Monitorar savegame…', command=self.choose_folder).pack(side='left', padx=5)
        ttk.Button(row, text='Abrir replay…', command=self.choose_file).pack(side='left')
        controls = ttk.Frame(page)
        controls.pack(fill='x')
        ttk.Label(controls, text='Largura').grid(row=0, column=0)
        tk.Spinbox(controls, from_=300, to=900, increment=20, textvariable=self.width, width=6, command=self.resize).grid(row=0, column=1)
        ttk.Label(controls, text='Opacidade').grid(row=1, column=0)
        ttk.Scale(controls, from_=0.2, to=1, variable=self.opacity, command=self.alpha).grid(row=1, column=1, sticky='ew')
        ttk.Checkbutton(controls, text='Exibir overlay · Ctrl+Alt+M', variable=self.show).grid(row=0, column=2, padx=15)
        ttk.Button(controls, text='Prévia por 10s', command=self.preview).grid(row=1, column=2)
        ttk.Button(page, text='Abrir relatórios e imagens', command=self.open_output).pack(anchor='w', pady=8)
        ttk.Label(page, textvariable=self.status, wraplength=800).pack(anchor='w', pady=8)
        ttk.Label(page, text='Relatório cumulativo — pesquisas solicitadas, conclusão não confirmada').pack(anchor='w')
        self.report = tk.Text(page, height=22, wrap='word', font=('Consolas', 10))
        self.report.pack(fill='both', expand=True)
        self.setup_position_controls(page)
        self.overlay = tk.Toplevel(root)
        self.overlay.withdraw()
        self.overlay.overrideredirect(True)
        self.overlay.attributes('-topmost', True)
        self.overlay.attributes('-alpha', 0.85)
        self.overlay.configure(bg='#101b24')
        self.image = tk.Label(self.overlay, bd=0, bg='#101b24')
        self.image.pack()
        self.overlay.update_idletasks()
        self.hwnd = native.u.GetAncestor(self.overlay.winfo_id(), 2)
        native.u.SetWindowLongW(self.hwnd, -20, native.u.GetWindowLongW(self.hwnd, -20) | 134742176)
        self.keys = queue.Queue()
        self.stop_keys = threading.Event()
        threading.Thread(target=self.watch_keys, daemon=True).start()
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.tick)

    def setup_position_controls(self, parent):
        self.position_corner = tk.StringVar(value='Superior direito')
        self.position_x = tk.StringVar(value='20')
        self.position_y = tk.StringVar(value='60')
        panel = ttk.LabelFrame(parent, text='Posição do overlay', padding=8)
        panel.pack(fill='x', pady=8, before=self.report)
        ttk.Combobox(panel, textvariable=self.position_corner, state='readonly', values=('Superior esquerdo', 'Superior direito', 'Inferior esquerdo', 'Inferior direito'), width=20).grid(row=0, column=0, padx=4)
        ttk.Label(panel, text='Margem horizontal (px)').grid(row=0, column=1)
        tk.Spinbox(panel, from_=0, to=10000, width=6, textvariable=self.position_x).grid(row=0, column=2, padx=4)
        ttk.Label(panel, text='Margem vertical (px)').grid(row=0, column=3)
        tk.Spinbox(panel, from_=0, to=10000, width=6, textvariable=self.position_y).grid(row=0, column=4, padx=4)
        ttk.Label(panel, text='Aplicação imediata. Use Prévia por 10s para conferir.').grid(row=1, column=0, columnspan=5, sticky='w', pady=(6, 0))

    def overlay_position(self, x, y, width, height, iw, ih):

        def margin(variable, default):
            try:
                return max(0, min(10000, int(variable.get())))
            except (ValueError, tk.TclError):
                return default
        mx = margin(self.position_x, 20)
        my = margin(self.position_y, 60)
        corner = self.position_corner.get()
        right = corner in ('Superior direito', 'Inferior direito')
        bottom = corner in ('Inferior esquerdo', 'Inferior direito')
        dx = width - iw - mx if right else mx
        dy = height - ih - my if bottom else my
        dx = max(0, min(max(0, width - iw), dx))
        dy = max(0, min(max(0, height - ih), dy))
        return (x + dx, y + dy)

    def watch_keys(self):
        registered = bool(self.native.u.RegisterHotKey(None, 21, 16387, 77))
        if not registered:
            self.keys.put('unavailable')
            return
        try:
            msg = W.MSG()
            while not self.stop_keys.wait(0.05):
                while self.native.u.PeekMessageW(C.byref(msg), None, 786, 786, 1):
                    if msg.wParam == 21:
                        self.keys.put('toggle')
        finally:
            self.native.u.UnregisterHotKey(None, 21)

    def choose_folder(self):
        folder = filedialog.askdirectory(title='Pasta savegame')
        if folder:
            self.folder.set(folder)
            self.baseline = set(Path(folder).glob('*.aoe2record'))
            self.status.set('Monitorando novos arquivos a cada 0,25s. Para uma partida já iniciada, use Abrir replay.')

    def choose_file(self):
        path = filedialog.askopenfilename(filetypes=[('Replay AoE2 DE', '*.aoe2record')])
        if path:
            self.attach(Path(path))

    def attach(self, path):
        self.epoch += 1
        self.path = Path(path)
        self.session = None
        self.pending = self.path
        self.next_frame = 0
        self.photo = None
        self.image.configure(image='')
        self.overlay.withdraw()
        self.report.delete('1.0', 'end')
        self.status.set('Aguardando cabeçalho completo: ' + self.path.name)

    def resize(self):
        self.next_frame = 0

    def alpha(self, *args):
        if hasattr(self, 'overlay'):
            self.overlay.attributes('-alpha', float(self.opacity.get()))

    def preview(self):
        self.show.set(True)
        self.preview_until = time.monotonic() + 10

    def target_width(self):
        try:
            width = min(900, max(300, int(self.width.get())))
        except (ValueError, tk.TclError):
            width = 480
        game = self.native.game()
        height = game[3] - 110 if game else self.root.winfo_screenheight() - 110
        available_width = game[2] - 40 if game else self.root.winfo_screenwidth() - 40
        return min(width, max(200, int(height * 900 / 1140)), max(200, available_width))

    def job(self, epoch, path, session, width):
        try:
            try:
                session = session or Session(path)
                session.poll()
            except (g.NotReady, PermissionError) as exc:
                self.queue.put((epoch, 'pending', session, str(exc)))
                return
            data = frame(session, ROOT / 'mapas_atualizados', width)
            self.queue.put((epoch, 'ok', session, data))
        except Exception as exc:
            __import__('logging').exception('Falha no processamento do minimapa')
            self.queue.put((epoch, 'error', session, str(exc)))

    def tick(self):
        now = time.monotonic()
        while not self.keys.empty():
            if self.keys.get_nowait() == 'toggle':
                self.show.set(not self.show.get())
            else:
                self.status.set('Atalho ocupado. Use a caixa Exibir overlay.')
        while not self.queue.empty():
            epoch, kind, session, data = self.queue.get_nowait()
            self.busy = False
            if epoch != self.epoch:
                continue
            self.session = session
            if kind == 'ok':
                self.pending = None
                self.photo = tk.PhotoImage(data=base64.b64encode(data['png']).decode())
                self.image.configure(image=self.photo)
                self.last_directory = data['directory']
                self.report.delete('1.0', 'end')
                self.report.insert('end', data['report'])
                source = 'finalizado' if data['state']['source_finished'] else 'aguardando novos registros'
                self.status.set(f"Quadro {data['state']['rendered_at']} | arquivo até {game_time(data['state']['game_ms'])} | {source}")
            elif kind == 'pending':
                self.pending = self.path
                self.next_frame = now + 0.25
                self.status.set(str(data))
            else:
                self.pending = None
                self.next_frame = float('inf')
                self.photo = None
                self.image.configure(image='')
                self.overlay.withdraw()
                self.status.set('Atualização interrompida: ' + str(data))
        if self.closing:
            if not self.busy:
                self.root.destroy()
                return
        else:
            if self.folder.get() and now - self.last_scan >= 0.25:
                self.last_scan = now
                try:
                    new = [p for p in Path(self.folder.get()).glob('*.aoe2record') if p not in self.baseline]
                    if new:
                        self.baseline.update(new)
                        self.attach(max(new, key=lambda p: p.stat().st_mtime_ns))
                except OSError as exc:
                    self.status.set('Pasta indisponível: ' + str(exc))
            if self.path and (not self.busy) and (now >= self.next_frame):
                self.busy = True
                self.next_frame = now
                threading.Thread(target=self.job, args=(self.epoch, self.path, self.session, self.target_width()), daemon=True).start()
            game = self.native.game()
            if self.photo and self.show.get() and (game or now < self.preview_until):
                x, y, width, height = game or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
                if hasattr(self, 'prepare_fit_photo'):
                    self.prepare_fit_photo()
                iw, ih = (self.photo.width(), self.photo.height())
                self.overlay.geometry(f'{iw}x{ih}')
                self.overlay.update_idletasks()
                ox, oy = self.overlay_position(x, y, width, height, iw, ih)
                self.native.u.SetWindowPos(self.hwnd, None, ox, oy, iw, ih, 20)
                self.overlay.deiconify()
            else:
                self.overlay.withdraw()
        self.root.after(10 if self.busy else 0 if self.path and now >= self.next_frame else 100, self.tick)

    def open_output(self):
        if self.last_directory:
            os.startfile(self.last_directory)

    def close(self):
        self.closing = True
        self.stop_keys.set()
        self.overlay.withdraw()
        self.status.set('Fechando após finalizar a geração em andamento…')
if __name__ == '__main__':
    native = Native()
    root = tk.Tk()
    Window(root, native)
    root.mainloop()
