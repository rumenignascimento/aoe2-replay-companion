"""Ordens militares de J2, com origens apenas de referência."""
from collections import Counter, deque
from fractions import Fraction
import base64
import json
import math
import os
from pathlib import Path
import re
import struct
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
import xml.etree.ElementTree as ET
import painel_aoe2 as panel
if not hasattr(panel, 'OrderSession'):
    raise RuntimeError('Instale primeiro a atualização ativar_pedidos_construcao.py.')
app = panel.app
mini = panel.minimap
NS = mini.NS
ROOT = Path(__file__).resolve().parent
COMMIT = 'e56728e76b7d08301fba7b18d5f16bc8554c109a'
SOURCE = f'https://raw.githubusercontent.com/SiegeEngineers/aoe2techtree/{COMMIT}/'
OPTIONS = (True, True, 60, 16)
AI_PARSE_LOCK = threading.RLock()
CIVILIAN_IDS = {13, 17, 83, 128, 293, 1808}
CIVILIAN_NAMES = {'villager', 'trade cart', 'trade cog', 'fishing ship', 'mule cart'}

def movement_session(base):

    class MovementSession(base):

        def __init__(self, path):
            super().__init__(path)
            self.move_history = deque(maxlen=500)
            self.move_latest = {}
            self.move_references = {}
            self.move_serial = 0
            self.move_omitted = 0
            self.move_ai_unsupported = 0
            self.military_production_orders = Counter()
            self.move_objects = {obj['id']: obj for obj in self.initial}

        def valid_destination(self, x, y):
            n = self.model['dimension']
            return isinstance(x, (int, float)) and isinstance(y, (int, float)) and math.isfinite(x) and math.isfinite(y) and (0 <= x < n) and (0 <= y < n)

        def poll(self, *args, **kwargs):
            with AI_PARSE_LOCK:
                original = self.fast.parse_action

                def decode(action, data):
                    payload = original(action, data)
                    if action.name == 'AI_ORDER' and self.model.get('build') == 188329 and (len(data) == 43) and (struct.unpack_from('<h', data, 1)[0] == 40):
                        count, obj, target, extra, task, x, y, z, flag = struct.unpack_from('<5I4f', data, 3)
                        if count == 1 and extra == 0 and (task == 705) and (target == 4294967295) and (z == -1.0) and (flag == 1.0) and self.valid_destination(x, y) and (payload.get('object_ids') == [obj]):
                            payload['_troop_ai_target'] = (x, y)
                    return payload
                self.fast.parse_action = decode
                try:
                    return super().poll(*args, **kwargs)
                finally:
                    self.fast.parse_action = original

        def apply(self, action, payload):
            super().apply(action, payload)
            if not hasattr(self, 'move_objects'):
                return
            owner = payload.get('player_id')
            ids = list(dict.fromkeys(payload.get('object_ids', [])))
            if owner is None and ids:
                known = self.move_objects.get(ids[0])
                owner = known.get('owner') if known else None
            if owner != 2:
                return
            if action in ('MAKE', 'DE_QUEUE', 'QUEUE'):
                kind = payload.get('unit_id')
                name = self.reference.get('objects', {}).get(str(kind), '')
                if isinstance(kind, int) and kind not in CIVILIAN_IDS and (str(name).casefold() not in CIVILIAN_NAMES) and (payload.get('amount', 1) > 0):
                    self.military_production_orders[kind] += 1
            if action in ('STOP', 'DELETE'):
                for ident in ids:
                    self.move_latest[ident] = -1
                return
            if action == 'AI_ORDER':
                target = payload.get('_troop_ai_target')
                if not target:
                    self.move_ai_unsupported += 1
                    return
                x, y = target
            elif action in ('MOVE', 'PATROL', 'DE_ATTACK_MOVE'):
                x, y = (payload.get('x'), payload.get('y'))
            elif action == 'ORDER' and payload.get('target_id') in (-1, 4294967295):
                x, y = (payload.get('x'), payload.get('y'))
            else:
                return
            if not self.valid_destination(x, y):
                return
            if not ids:
                self.move_omitted += 1
                return
            self.move_serial += 1
            members = []
            for ident in ids:
                obj = self.move_objects.get(ident)
                reference = self.move_references.get(ident)
                if reference is None and obj and self.valid_destination(obj['x'], obj['y']):
                    reference = (obj['x'], obj['y'], 'initial')
                self.move_references[ident] = (x, y, 'previous_target')
                self.move_latest[ident] = self.move_serial
                if obj and (obj['kind'] != 'unit' or obj['type_id'] in CIVILIAN_IDS or str(obj['name']).casefold() in CIVILIAN_NAMES):
                    continue
                members.append({'id': ident, 'type_id': obj['type_id'] if obj else None, 'name': obj['name'] if obj else 'Tipo desconhecido', 'origin': reference})
            if members:
                self.move_history.append({'serial': self.move_serial, 'ms': self.ms, 'destination': [x, y], 'members': members, 'action': action})

        def movements(self, horizon=60000, limit=3):
            result = []
            for event in reversed(self.move_history):
                if event['ms'] < self.ms - horizon:
                    continue
                groups = {}
                for member in event['members']:
                    if self.move_latest.get(member['id']) != event['serial']:
                        continue
                    key = member['type_id']
                    group = groups.setdefault(key, {'type_id': key, 'name': member['name'], 'count': 0, 'origins': [], 'type_source': 'initial_snapshot' if key is not None else 'unknown'})
                    group['count'] += 1
                    if member['origin'] is not None:
                        group['origins'].append(member['origin'])
                for group in groups.values():
                    origins = group.pop('origins')
                    group['origin'] = [sum((o[0] for o in origins)) / len(origins), sum((o[1] for o in origins)) / len(origins)] if origins else None
                    group['origin_count'] = len(origins)
                    group['origin_sources'] = sorted({o[2] for o in origins})
                if groups:
                    result.append({'ms': event['ms'], 'destination': event['destination'], 'groups': list(groups.values()), 'action': event['action']})
                if len(result) >= limit:
                    break
            return result
    return MovementSession

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.tropas-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)

class UnitIcons:

    def __init__(self):
        self.data = {}
        self.civs = set()
        self.attempted = set()
        self.images = {}
        self.errors = []

    def tree(self, civ):
        civ = re.sub('[^A-Za-z]', '', str(civ)).upper()
        if not civ or civ in self.civs:
            return
        self.civs.add(civ)
        path = ROOT / 'icones_aoe2' / f'unidades_{civ}.json'
        try:
            if path.exists():
                document = json.loads(path.read_text('utf-8'))
            else:
                with urllib.request.urlopen(SOURCE + f'data/trees/{civ}.json', timeout=15) as response:
                    raw = response.read(2 * 1024 * 1024 + 1)
                if len(raw) > 2 * 1024 * 1024:
                    raise ValueError('Metadados muito grandes.')
                document = json.loads(raw)
                atomic_write(path, raw)
            nodes = document['units_techs']
            if isinstance(nodes, dict):
                nodes = nodes.values()
            for node in nodes:
                if node.get('use_type') == 'Unit':
                    self.data[node['node_id']] = {'name': node['name'], 'picture': node['picture_index']}
        except Exception as exc:
            self.errors.append(f'Ícones de {civ}: {exc}')

    def military(self, ident):
        record = self.data.get(ident)
        return bool(record and ident not in CIVILIAN_IDS and (record['name'].casefold() not in CIVILIAN_NAMES))

    def prepare(self, session):
        self.tree('BRITONS')
        for player in session.model['players']:
            if player['slot'] == 2:
                self.tree(player['civilization'])
        kinds = {obj['type_id'] for obj in session.initial if obj['kind'] == 'unit' and obj['owner'] == 2}
        kinds.update(session.military_production_orders)
        for ident in kinds:
            if ident not in self.data:
                name = session.reference.get('objects', {}).get(str(ident), '')
                alias = next((record for record in self.data.values() if record['name'] == name), None)
                if alias:
                    self.data[ident] = alias
            if not self.military(ident) or ident in self.attempted:
                continue
            self.attempted.add(ident)
            path = ROOT / 'icones_aoe2' / f'troop_{ident}.png'
            try:
                data = path.read_bytes() if path.exists() else b''
                if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                    picture = self.data[ident]['picture']
                    with urllib.request.urlopen(SOURCE + f'img/Unit/{picture}.png', timeout=15) as response:
                        data = response.read(256 * 1024 + 1)
                    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                        raise ValueError('PNG inválido.')
                    atomic_write(path, data)
                self.images[ident] = data
            except Exception as exc:
                self.errors.append(f'Ícone {ident}: {exc}')
ICONS = UnitIcons()
OriginalSession = panel.OrderSession
panel.OrderSession = movement_session(OriginalSession)
_original_frame = app.frame

def frame_with_icons(session, *args, **kwargs):
    ICONS.prepare(session)
    return _original_frame(session, *args, **kwargs)
app.frame = frame_with_icons
_base_order_state = panel.order_state

def state_with_troops(session):
    state = _base_order_state(session)
    state['troop_movements'] = session.movements(OPTIONS[2] * 1000, 3)
    state['military_orders'] = {kind: count for kind, count in session.military_production_orders.items() if ICONS.military(kind)}
    state['movement_selection_omitted'] = session.move_omitted
    state['ai_orders_ignored'] = session.move_ai_unsupported
    return state
panel.order_state = state_with_troops
_base_report = panel.state_report

def report_with_troops(state):
    lines = [_base_report(state), '', 'J2 — ÚLTIMAS ORDENS IDENTIFICÁVEIS DE DESLOCAMENTO', 'R = posição inicial ou destino anterior associado aos mesmos IDs; não é partida confirmada.', 'Setas indicam pedidos, não trajetos percorridos nem posições atuais.', 'Tipos identificados vêm do estado inicial; alterações posteriores não são confirmadas.', 'Tipo desconhecido pode incluir unidades civis. Não inferimos tipos pelas filas de produção.']
    events = state.get('troop_movements', [])
    if not events:
        lines.append('Nenhuma ordem com seleção utilizável na janela de tempo escolhida.')
    for event in events:
        lines.append(f"{app.base.game_time(event['ms'])} → destino {event['destination']}")
        for group in event['groups']:
            origin = str(group['origin']) if group['origin'] is not None else 'indisponível'
            lines.append(f"  {group['count']} {group['name']} | referência: {origin} | origens disponíveis: {group['origin_count']}/{group['count']}")
    lines.extend(['', 'J2 — PEDIDOS DE PRODUÇÃO MILITAR (não unidades produzidas)'])
    for ident, count in state.get('military_orders', {}).items():
        lines.append(f"{ICONS.data[ident]['name']}: {count} comando(s) de produção")
    lines.append(f"Ordens com seleção omitida não reconstruída: {state.get('movement_selection_omitted', 0)}")
    if ICONS.errors:
        lines.extend(ICONS.errors[-3:])
    return '\n'.join(lines)
panel.state_report = report_with_troops
_projection = mini.project
_projection_context = threading.local()

def tracked_project(x, y, n, turns=0, mirror=False):
    _projection_context.options = (turns, mirror)
    return _projection(x, y, n, turns, mirror)
mini.project = tracked_project
_base_map = mini.minimap_svg

def movement_map(session):
    _projection_context.options = None
    root = ET.fromstring(_base_map(session))
    options = _projection_context.options or mini.SETTINGS[:2]
    show, _, seconds, size = OPTIONS
    if not show:
        return ET.tostring(root, encoding='unicode')
    events = session.movements(seconds * 1000, 3)
    if not events:
        return ET.tostring(root, encoding='unicode')

    def add(parent, tag, **attrs):
        return ET.SubElement(parent, '{' + NS + '}' + tag, {key: str(value) for key, value in attrs.items()})
    layer = root.find('{' + NS + '}g[@clip-path="url(#map-area)"]')
    defs = root.find('{' + NS + '}defs')
    if layer is None or defs is None:
        return ET.tostring(root, encoding='unicode')
    label_layer = add(root, 'g')
    colors = {player['number']: player['color_id'] for player in session.header.get('de', {}).get('players', []) if player.get('number', -1) > 0 and 0 <= player.get('color_id', -1) < 8}
    color = mini.PLAYER_COLORS[colors.get(2, 1)]
    marker = add(defs, 'marker', id='troop-arrow', viewBox='0 0 10 10', refX=9, refY=5, markerWidth=5, markerHeight=5, orient='auto-start-reverse')
    add(marker, 'path', d='M0 0L10 5L0 10Z', fill=color)
    embedded = set()

    def point(coords):
        return _projection(coords[0], coords[1], session.model['dimension'], options[0], options[1])
    for event in events:
        tx, ty = point(event['destination'])
        add(layer, 'circle', cx=tx, cy=ty, r=3, fill='none', stroke=color, **{'stroke-width': 2})
        groups = event['groups']
        step = size + 20
        start = min(890 - len(groups) * step, max(10, tx - len(groups) * step / 2))
        yy = min(430 - size, max(5, ty - size - 12))
        for index, group in enumerate(groups):
            origin = group['origin']
            if origin is not None:
                ox, oy = point(origin)
                add(layer, 'line', x1=ox, y1=oy, x2=tx, y2=ty, stroke=color, **{'stroke-width': 1.5, 'stroke-dasharray': '4 3', 'marker-end': 'url(#troop-arrow)'})
                add(layer, 'circle', cx=ox, cy=oy, r=3, fill='none', stroke=color)
                add(layer, 'text', x=ox + 4, y=oy - 4, fill='white', **{'font-size': 10}).text = 'R'
            xx = start + index * step
            ident = group['type_id']
            image = ICONS.images.get(ident)
            if image:
                key = f'troop-image-{ident}'
                if ident not in embedded:
                    add(defs, 'image', id=key, href='data:image/png;base64,' + base64.b64encode(_unidade_transparente_0411(image)).decode('ascii'), width=54, height=54, x=-3, y=-3)
                    embedded.add(ident)
                node = add(label_layer, 'g', transform=f'translate({xx} {yy}) scale({size / 48})')
                add(node, 'use', href='#' + key)
            else:
                add(label_layer, 'text', x=xx + size / 2, y=yy + size, fill='white', **{'font-size': size, 'text-anchor': 'middle'}).text = '?'
            add(label_layer, 'text', x=xx + size + 2, y=yy + size * 0.85, fill='white', **{'font-family': 'Segoe UI,Arial', 'font-size': 12, 'font-weight': 'bold'}).text = str(group['count'])
    return ET.tostring(root, encoding='unicode')
mini.minimap_svg = movement_map
app.map_svg = movement_map
EXTRA_DEFAULTS = {'troops_map': True, 'troops_bar': True, 'troops_seconds': 60, 'troops_icon_size': 16}
if hasattr(panel, 'CONFIG_DEFAULTS'):
    panel.CONFIG_DEFAULTS.update(EXTRA_DEFAULTS)
    _base_validate = panel._validate_config

    def validate_options(values):
        result = _base_validate(values)
        for key, low, high in (('troops_seconds', 5, 300), ('troops_icon_size', 10, 40)):
            value = result[key]
            if isinstance(value, bool):
                raise ValueError(key + ': número inválido.')
            number = float(value)
            if not low <= number <= high or int(number) != number:
                raise ValueError(key + ': valor fora do intervalo.')
            result[key] = int(number)
        return result
    panel._validate_config = validate_options

def bar_entries(state, show_units):
    rows = [('building', ident, count) for ident, count in panel.building_entries(state) or ()]
    if show_units:
        rows.extend((('unit', int(ident), count) for ident, count in state.get('military_orders', {}).items() if count > 0))
    return rows

class Window(panel.Window):

    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)
        self.troops_map = tk.BooleanVar(value=True)
        self.troops_bar = tk.BooleanVar(value=True)
        self.troops_seconds = tk.IntVar(value=60)
        self.troops_icon_size = tk.IntVar(value=16)
        box = ttk.LabelFrame(parent, text='Tropas — ordens do jogador 2', padding=8)
        box.pack(fill='x', pady=6, before=self.report)
        ttk.Checkbutton(box, text='Deslocamentos no minimapa', variable=self.troops_map).grid(row=0, column=0)
        ttk.Checkbutton(box, text='Produção militar na barra', variable=self.troops_bar).grid(row=0, column=1)
        ttk.Label(box, text='Últimos segundos do replay').grid(row=1, column=0)
        tk.Spinbox(box, from_=5, to=300, textvariable=self.troops_seconds, width=6).grid(row=1, column=1)
        ttk.Label(box, text='Tamanho dos ícones das tropas').grid(row=2, column=0)
        tk.Spinbox(box, from_=10, to=40, textvariable=self.troops_icon_size, width=6).grid(row=2, column=1)
        ttk.Label(box, text='R = referência de origem. ? = tipo desconhecido. Setas representam pedidos.').grid(row=3, column=0, columnspan=2, sticky='w')
        ttk.Label(box, text='Na barra, os números militares contam comandos de produção; não unidades produzidas.').grid(row=4, column=0, columnspan=2, sticky='w')
        for variable in (self.troops_map, self.troops_bar, self.troops_seconds, self.troops_icon_size):
            variable.trace_add('write', self.troop_options)

    def troop_options(self, *args):
        global OPTIONS
        try:
            OPTIONS = (bool(self.troops_map.get()), bool(self.troops_bar.get()), max(5, min(300, int(self.troops_seconds.get()))), max(10, min(40, int(self.troops_icon_size.get()))))
        except (ValueError, tk.TclError):
            return
        self.bar_cache = None
        self.next_frame = 0

    def __init__(self, root, native):
        super().__init__(root, native)
        self.troop_options()
        root.title('AoE2 — pedidos de construção, produção e deslocamento de J2')

    def draw_bar(self, size):
        rows = bar_entries(self.bar_state, self.troops_bar.get())
        self.canvas.delete('all')
        pad = max(3, round(size * 0.12))
        row = max(1, round(size * 1.25))
        for index, (kind, ident, count) in enumerate(rows):
            yy = pad + index * row
            if kind == 'building':
                self.draw_building_icon(ident, pad, yy, size)
            else:
                if not hasattr(self, '_troop_photos'):
                    self._troop_photos = {}
                    self._troop_photo_size = None
                if self._troop_photo_size != size:
                    self._troop_photos.clear()
                    self._troop_photo_size = size
                if ident not in self._troop_photos and ident in ICONS.images:
                    original = tk.PhotoImage(master=self.root, data=base64.b64encode(ICONS.images[ident]).decode())
                    ratio = Fraction(size, max(original.width(), original.height())).limit_denominator(8)
                    self._troop_photos[ident] = original.zoom(ratio.numerator).subsample(ratio.denominator)
                image = self._troop_photos.get(ident)
                if image:
                    self.canvas.create_image(pad + size / 2, yy + size / 2, image=image)
                else:
                    self.canvas.create_text(pad + size / 2, yy + size / 2, text='?', fill='white')
            self.canvas.create_text(pad + size * 1.6, yy + size * 0.5, text=f'{count}?', fill='white', font=('Segoe UI', max(9, round(size * 0.48)), 'bold'))
        width = round(size * 2.4) + pad * 2
        height = max(1, pad * 2 + row * len(rows))
        self.canvas.configure(width=width, height=height)
        self.caption_size = (width, height)

    def tick(self):
        app.base.Window.tick(self)
        if self.closing:
            return
        rows = bar_entries(self.bar_state, self.troops_bar.get())
        game = self.native.game()
        if not (rows and self.photo and self.caption_show.get() and (game or time.monotonic() < self.preview_until)):
            self.caption.withdraw()
            return
        x, y, w, h = game or (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())

        def number(variable, default, low, high):
            try:
                return min(high, max(low, int(variable.get())))
            except (ValueError, tk.TclError):
                return default
        size = min(number(self.bar_size, 48, 24, 120), max(1, int((h - 8) / (len(rows) * 1.25 + 0.3))), max(1, int((w - 8) / 2.7)))
        cache = (tuple(rows), size)
        if cache != self.bar_cache:
            self.draw_bar(size)
            self.bar_cache = cache
        self.caption.attributes('-alpha', float(self.bar_opacity.get()))
        iw, ih = self.caption_size
        mx = number(self.caption_x, 20, 0, 10000)
        my = number(self.caption_y, 80, 0, 10000)
        corner = self.caption_corner.get()
        dx = w - iw - mx if corner in ('Superior direito', 'Inferior direito') else mx
        dy = h - ih - my if corner in ('Inferior esquerdo', 'Inferior direito') else my
        self.caption.geometry(f'{iw}x{ih}')
        self.caption.update_idletasks()
        self.native.u.SetWindowPos(self.caption_hwnd, None, x + max(0, min(max(0, w - iw), dx)), y + max(0, min(max(0, h - ih), dy)), iw, ih, 20)
        self.caption.deiconify()
if __name__ == '__main__':
    native = app.base.Native()
    root = tk.Tk()
    Window(root, native)
    root.mainloop()
from functools import lru_cache as _cache_icone_0411

@_cache_icone_0411(maxsize=512)
def _unidade_transparente_0411(raw):
    import io
    from collections import deque
    from PIL import Image, ImageChops, ImageFilter
    with Image.open(io.BytesIO(raw)) as source:
        image = source.convert('RGBA')
    width, height = image.size
    pixels = image.load()
    seen = set()
    queue = deque()

    def background(x, y):
        r, g, b, a = pixels[x, y]
        return a == 0 or (max(r, g, b) <= 16 and max(r, g, b) - min(r, g, b) <= 12)

    def visit(x, y):
        if (x, y) not in seen and background(x, y):
            seen.add((x, y))
            queue.append((x, y))
    for x in range(width):
        visit(x, 0)
        visit(x, height - 1)
    for y in range(height):
        visit(0, y)
        visit(width - 1, y)
    while queue:
        x, y = queue.popleft()
        r, g, b, a = pixels[x, y]
        pixels[x, y] = (r, g, b, 0)
        for xx, yy in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= xx < width and 0 <= yy < height:
                visit(xx, yy)
    padded = Image.new('RGBA', (width + 6, height + 6))
    padded.alpha_composite(image, (3, 3))
    alpha = padded.getchannel('A')
    outer = alpha.filter(ImageFilter.MaxFilter(7))
    inner = alpha.filter(ImageFilter.MaxFilter(3))
    result = Image.new('RGBA', padded.size, '#111915')
    result.putalpha(outer)
    light = Image.new('RGBA', padded.size, '#fff1bc')
    light.putalpha(inner)
    result = Image.alpha_composite(result, light)
    result = Image.alpha_composite(result, padded)
    if result.size != (54, 54):
        result = result.resize((54, 54), Image.Resampling.LANCZOS)
    output = io.BytesIO()
    result.save(output, format='PNG')
    return output.getvalue()
