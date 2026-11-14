"""Minimapa com orientação ajustável e moldura discreta."""
import sys
import tkinter as tk
from tkinter import ttk
import xml.etree.ElementTree as ET
import overlay_legendas as app
NS = app.NS
KEY = app.KEY
SETTINGS = (0, False, False)
PLAYER_COLORS = ('#0066ff', '#ff2020', '#00cc00', '#ffff00', '#00ffff', '#ff00aa', '#aaaaaa', '#ff8800')

def project(x, y, n, turns=0, mirror=False):
    for _ in range(turns % 4):
        x, y = (n - y, x)
    if mirror:
        x = n - x
    return (450 + (x - y) * 420 / n, 15 + (x + y) * 210 / n)

def _minimap_without_buildings(session, _options):
    turns, mirror, terrain = _options
    n = session.model['dimension']
    root = ET.Element('{' + NS + '}svg', {'width': '900', 'height': '450', 'viewBox': '0 0 900 450', 'shape-rendering': 'crispEdges'})

    def add(parent, tag, **attrs):
        return ET.SubElement(parent, '{' + NS + '}' + tag, {k: str(v) for k, v in attrs.items()})

    def position(x, y):
        return project(x, y, n, turns, mirror)

    def polygon(parent, points, **attrs):
        return add(parent, 'polygon', points=' '.join((f'{x:.3f},{y:.3f}' for x, y in points)), **attrs)
    border = [(450, 15), (870, 225), (450, 435), (30, 225)]
    add(root, 'rect', width=900, height=450, fill=KEY)
    defs = add(root, 'defs')
    clip = add(defs, 'clipPath', id='map-area')
    polygon(clip, border)
    layer = add(root, 'g', **{'clip-path': 'url(#map-area)'})
    if terrain:
        palette = {0: '#8c9950', 1: '#38759a', 2: '#b5a46f', 17: '#729047', 27: '#ad9a65', 89: '#849549', 128: '#8c9950'}
        tiles = session.model['tiles']
        for y in range(n):
            x = 0
            while x < n:
                terrain_id, height = tiles[y * n + x]
                end = x + 1
                while end < n and tiles[y * n + end] == tiles[y * n + x]:
                    end += 1
                polygon(layer, [position(x, y), position(end, y), position(end, y + 1), position(x, y + 1)], fill=palette.get(terrain_id, '#8c9950'))
                x = end
    colors = {p['number']: p['color_id'] for p in session.header.get('de', {}).get('players', []) if p.get('number', -1) > 0 and 0 <= p.get('color_id', -1) < 8}

    def owner_color(owner):
        fallback = owner - 1 if isinstance(owner, int) and owner > 0 else 6
        index = colors.get(owner, fallback)
        return PLAYER_COLORS[index % len(PLAYER_COLORS)]

    def valid(x, y):
        return isinstance(x, (int, float)) and isinstance(y, (int, float)) and (0 <= x < n) and (0 <= y < n)

    def dot(x, y, size, color):
        px, py = position(x, y)
        add(layer, 'rect', x=round(px - size / 2), y=round(py - size / 2), width=size, height=size, fill=color)
    resources = {'madeira': '#006b00', 'ouro': '#ffd600', 'pedra': '#b8b8b8', 'frutas': '#e00030', 'caca': '#c09050', 'rebanho': '#eeeecc', 'peixes': '#38a8d8', 'reliquias': '#ffffff'}
    for point in session.model['points']:
        kind = point['kind']
        if kind not in resources or not valid(point['x'], point['y']):
            continue
        size = max(2, round(420 / n * 0.65)) if kind == 'madeira' else 4
        dot(point['x'], point['y'], size, resources[kind])
    for event in list(session.build_requests)[-80:]:
        if not valid(event.get('x'), event.get('y')):
            continue
        x, y = position(event['x'], event['y'])
        node = add(layer, 'rect', x=round(x - 4), y=round(y - 4), width=8, height=8, fill='none', stroke=owner_color(event.get('player')), **{'stroke-width': 1, 'stroke-dasharray': '2 2'})
        add(node, 'title').text = 'Pedido histórico; conclusão não confirmada.'
    for obj in session.initial:
        if obj['type_id'] in app.base.g.TC_IDS or not valid(obj['x'], obj['y']):
            continue
        dot(obj['x'], obj['y'], 4 if obj['kind'] == 'unit' else 7, owner_color(obj['owner']))
    for point in session.model['points']:
        if point['kind'] != 'centros' or not valid(point['x'], point['y']):
            continue
        owner = point['owner']
        dot(point['x'], point['y'], 11, owner_color(owner))
        x, y = position(point['x'], point['y'])
        label = add(layer, 'text', x=round(x + 8), y=round(y - 7), fill='white', **{'font-family': 'Segoe UI, Arial', 'font-size': 14, 'font-weight': 'bold'})
        label.text = f'J{owner}'
        add(label, 'title').text = f'Centro urbano inicial do jogador {owner}.'
    polygon(root, border, fill='none', stroke='#493e2d', **{'stroke-width': 4})
    polygon(root, border, fill='none', stroke='#a08c68', **{'stroke-width': 1})
    return ET.tostring(root, encoding='unicode')
MAP_BUILDING_ICONS = {12: ('Barracks', 'building_12.png'), 45: ('Dock', 'building_45.png'), 49: ('Siege Workshop', 'building_49.png'), 50: ('Farm', 'building_50.png'), 68: ('Mill', 'building_68.png'), 70: ('House', 'building_70.png'), 72: ('Palisade Wall', 'building_72.png'), 79: ('Watch Tower', 'building_79.png'), 82: ('Castle', 'building_82.png'), 84: ('Market', 'building_84.png'), 87: ('Archery Range', 'building_87.png'), 101: ('Stable', 'building_101.png'), 103: ('Blacksmith', 'building_103.png'), 104: ('Monastery', 'building_104.png'), 109: ('Town Center', 'building_109.png'), 117: ('Stone Wall', 'building_117.png'), 155: ('Fortified Wall', 'building_155.png'), 209: ('University', 'building_209.png'), 234: ('Guard Tower', 'building_234.png'), 235: ('Keep', 'building_235.png'), 236: ('Bombard Tower', 'building_236.png'), 276: ('Wonder', 'building_276.png'), 487: ('Gate', 'building_487.png'), 562: ('Lumber Camp', 'building_562.png'), 584: ('Mining Camp', 'building_584.png'), 598: ('Outpost', 'building_598.png'), 621: ('Town Center', 'building_621.png'), 792: ('Palisade Gate', 'building_792.png'), 1021: ('Feitoria', 'building_1021.png'), 1251: ('Krepost', 'building_1251.png'), 1665: ('Donjon', 'building_1665.png'), 1734: ('Folwark', 'building_1734.png'), 1754: ('Caravanserai', 'building_1754.png'), 1806: ('Fortified Church', 'building_1806.png'), 1808: ('Mule Cart', 'building_1808.png'), 1889: ('Pasture', 'building_1889.png'), 2556: ('Settlement', 'building_2556.png')}
MAP_ICON_SIZE = 18

def _marca_minimapa_0415(root):
    tag = '{' + NS + '}'
    for node in list(root):
        if node.get('id') == 'aoe2-brand-0415':
            root.remove(node)
    group = ET.SubElement(root, tag + 'g', {'id': 'aoe2-brand-0415', 'transform': 'translate(66 192) rotate(-26.5650511771)', 'pointer-events': 'none', 'shape-rendering': 'geometricPrecision', 'opacity': '0.96', 'aria-label': 'AoE II · Replay Companion'})
    ET.SubElement(group, tag + 'title').text = 'AoE II · Replay Companion'
    ET.SubElement(group, tag + 'path', {'d': 'M-9 -6L-5 -10L-1 -6L-5 -2Z', 'fill': '#d8b77c', 'stroke': '#18201b', 'stroke-width': '0.8'})
    ET.SubElement(group, tag + 'text', {'x': '4', 'y': '0', 'font-family': 'Georgia, Cambria, Times New Roman, serif', 'font-size': '17', 'font-weight': 'bold', 'letter-spacing': '0.35', 'fill': '#d8b77c', 'stroke': '#18201b', 'stroke-width': '0.55', 'paint-order': 'stroke fill', 'text-rendering': 'optimizeLegibility'}).text = 'AoE II · Replay Companion'

def minimap_svg(session):
    import base64
    from pathlib import Path
    from types import SimpleNamespace
    options = SETTINGS
    model = dict(session.model)
    model['points'] = [p for p in session.model['points'] if p['kind'] != 'centros']
    proxy = SimpleNamespace(model=model, header=session.header, initial=[o for o in session.initial if o['kind'] == 'unit'], build_requests=())
    root = ET.fromstring(_minimap_without_buildings(proxy, options))
    layer = root.find('{' + NS + '}g[@clip-path="url(#map-area)"]')
    defs = root.find('{' + NS + '}defs')
    if layer is None or defs is None:
        raise RuntimeError('A versão do minimapa não contém a camada esperada.')

    def add(parent, tag, **attrs):
        return ET.SubElement(parent, '{' + NS + '}' + tag, {k: str(v) for k, v in attrs.items()})
    n = session.model['dimension']

    def valid(x, y):
        return isinstance(x, (int, float)) and isinstance(y, (int, float)) and (0 <= x < n) and (0 <= y < n)
    colors = {p['number']: p['color_id'] for p in session.header.get('de', {}).get('players', []) if p.get('number', -1) > 0 and 0 <= p.get('color_id', -1) < 8}

    def owner_color(owner):
        fallback = owner - 1 if isinstance(owner, int) and owner > 0 else 6
        index = colors.get(owner, fallback)
        return PLAYER_COLORS[index % len(PLAYER_COLORS)]
    names = {value[0].casefold(): ident for ident, value in MAP_BUILDING_ICONS.items()}
    cache = {}

    def image_id(ident):
        if ident not in MAP_BUILDING_ICONS:
            name = session.reference.get('objects', {}).get(str(ident), '')
            ident = names.get(str(name).casefold())
        if ident not in MAP_BUILDING_ICONS:
            return None
        if ident in cache:
            return cache[ident]
        path = Path(__file__).resolve().parent / 'icones_aoe2' / MAP_BUILDING_ICONS[ident][1]
        try:
            data = path.read_bytes()
        except OSError:
            cache[ident] = None
            return None
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):
            cache[ident] = None
            return None
        key = f'map-building-{ident}'
        clip_0411 = ''
        if ident in app.base.g.TC_IDS or ident in (109, 621):
            clip_0411 = key + '-rounded'
            clip = add(defs, 'clipPath', id=clip_0411, clipPathUnits='userSpaceOnUse')
            add(clip, 'rect', x=0, y=0, width=48, height=48, rx=11.5, ry=11.5)
        add(defs, 'image', id=key, width=48, height=48, href='data:image/png;base64,' + base64.b64encode(data).decode('ascii'), **{'clip-path': 'url(#' + clip_0411 + ')' if clip_0411 else 'none', 'shape-rendering': 'geometricPrecision'})
        cache[ident] = key
        return key
    markers = {}

    def register(owner, ident, x, y, pending):
        if not valid(x, y):
            return
        key = (owner, ident, round(x, 3), round(y, 3))
        markers[key] = (owner, ident, x, y, pending)
    for obj in session.initial:
        if obj['kind'] == 'building':
            register(obj['owner'], obj['type_id'], obj['x'], obj['y'], False)
    for point in session.model['points']:
        if point['kind'] != 'centros':
            continue
        already_present = any((owner == point['owner'] and abs(x - point['x']) < 0.01 and (abs(y - point['y']) < 0.01) for owner, ident, x, y, pending in markers.values()))
        if not already_present:
            register(point['owner'], point['id'], point['x'], point['y'], False)
    for event in session.build_requests:
        ident = event.get('building_id')
        if isinstance(ident, int):
            register(event.get('player'), ident, event.get('x'), event.get('y'), True)
    for owner, ident, x, y, pending in markers.values():
        px, py = project(x, y, n, options[0], options[1])
        size = MAP_ICON_SIZE
        node = add(layer, 'g', **{'data-building-id': ident, 'data-kind': 'order' if pending else 'initial', 'data-owner': owner, 'data-map-x': px, 'data-map-y': py})
        add(node, 'title').text = f'J{owner}: pedido de construção; conclusão não confirmada.' if pending else f'J{owner}: construção no estado inicial do replay.'
        key = image_id(ident)
        if key:
            add(node, 'rect', x=px - size / 2 - 1, y=py - size / 2 - 1, width=size + 2, height=size + 2, fill='none', stroke=owner_color(owner), **{'stroke-width': 1}, rx=(size + 2) * 0.24 if ident in app.base.g.TC_IDS or ident in (109, 621) else 0, ry=(size + 2) * 0.24 if ident in app.base.g.TC_IDS or ident in (109, 621) else 0)
            scaled = add(node, 'g', transform=f'translate({px - size / 2} {py - size / 2}) scale({size / 48})')
            add(scaled, 'use', href='#' + key)
        else:
            add(node, 'text', x=px, y=py + 5, fill=owner_color(owner), **{'font-size': 18, 'text-anchor': 'middle'}).text = '?'
        if pending:
            add(node, 'text', x=px + size / 2 - 4, y=py - size / 2 + 8, fill='white', **{'font-family': 'Segoe UI,Arial', 'font-size': 12, 'font-weight': 'bold'}).text = '?'
        if ident in app.base.g.TC_IDS:
            add(node, 'text', x=px + size / 2 + 3, y=py - size / 2 - 3, fill='white', **{'font-family': 'Segoe UI,Arial', 'font-size': 14, 'font-weight': 'bold'}).text = f'J{owner}'
    _marca_minimapa_0415(root)
    return ET.tostring(root, encoding='unicode')
original_export = app.export_clean_png

def export_minimap(svg, png):
    tree = ET.parse(svg)
    root = tree.getroot()
    width = int(root.get('width'))
    root.set('height', str(max(1, round(width / 2))))
    tree.write(svg, encoding='unicode')
    original_export(svg, png)
OriginalWindow = app.Window

class MinimapWindow(OriginalWindow):

    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)
        self.map_turn = tk.StringVar(value='0°')
        self.map_mirror = tk.BooleanVar(value=False)
        self.map_terrain = tk.BooleanVar(value=False)
        panel = ttk.LabelFrame(parent, text='Orientação e aparência do minimapa', padding=8)
        panel.pack(fill='x', pady=6, before=self.report)
        ttk.Label(panel, text='Rotação').grid(row=0, column=0, padx=4)
        ttk.Combobox(panel, textvariable=self.map_turn, values=('0°', '90°', '180°', '270°'), state='readonly', width=7).grid(row=0, column=1)
        ttk.Checkbutton(panel, text='Espelhar', variable=self.map_mirror).grid(row=0, column=2, padx=8)
        ttk.Checkbutton(panel, text='Mostrar terreno', variable=self.map_terrain).grid(row=0, column=3, padx=8)
        ttk.Label(panel, text='J1/J2 indicam centros urbanos iniciais. A moldura acompanha o mapa.').grid(row=1, column=0, columnspan=4, sticky='w', pady=(5, 0))
        for variable in (self.map_turn, self.map_mirror, self.map_terrain):
            variable.trace_add('write', self.map_options)

    def map_options(self, *args):
        global SETTINGS
        SETTINGS = (('0°', '90°', '180°', '270°').index(self.map_turn.get()), bool(self.map_mirror.get()), bool(self.map_terrain.get()))
        self.next_frame = 0
app.map_svg = minimap_svg
app.export_clean_png = export_minimap
app.Window = MinimapWindow
if __name__ == '__main__':
    sys.modules['minimapa_aoe2'] = sys.modules[__name__]
    import painel_aoe2 as panel
    native = app.base.Native()
    root = tk.Tk()
    panel.Window(root, native)
    root.mainloop()
