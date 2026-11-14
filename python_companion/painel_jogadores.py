"""Todos os jogadores, filtro compartilhado e atalhos configuráveis."""
from collections import Counter, defaultdict, deque
import base64
import copy
from fractions import Fraction
import json
import math
from pathlib import Path
import queue
import re
import threading
import time
import tkinter as tk
from tkinter import ttk
import urllib.request
import xml.etree.ElementTree as ET
import painel_melhorado as m
p, t, app, mini = (m.p, m.t, m.app, m.mini)
NS = m.NS
SELECTION = (0, 0)
CONTEXT = threading.local()

def selection():
    return getattr(CONTEXT, 'selection', SELECTION)

def roster(session):
    return sorted((a['slot'] for a in session.model['players'] if a['slot'] > 0))

def selected_ids(session):
    owner = selection()[0]
    ids = roster(session)
    return ids if owner == 0 else [owner] if owner in ids else []
BaseSession = p.OrderSession

class AllSession(BaseSession):

    def __init__(self, path):
        super().__init__(path)
        self.all_buildings = defaultdict(Counter)
        self.all_production = defaultdict(Counter)
        self.all_moves = deque(maxlen=4000)
        self.all_latest = {}
        self.all_refs = {}
        self.all_serial = 0
        self.all_omitted = Counter()
        self.all_ai_ignored = Counter()
        self.all_objects = {o['id']: o for o in self.initial}
        self.all_players = set(roster(self))

    def apply(self, action, payload):
        super().apply(action, payload)
        if not hasattr(self, 'all_players'):
            return
        owner = payload.get('player_id')
        ids = list(dict.fromkeys(payload.get('object_ids', [])))
        if owner is None and ids:
            obj = self.all_objects.get(ids[0])
            owner = obj['owner'] if obj else None
        if owner not in self.all_players:
            return
        ident = payload.get('building_id')
        if action == 'BUILD' and ident in p.BUILDING_CATALOG:
            self.all_buildings[owner][ident] += 1
        if action in ('MAKE', 'DE_QUEUE', 'QUEUE'):
            kind = payload.get('unit_id')
            name = self.reference.get('objects', {}).get(str(kind), '')
            if isinstance(kind, int) and kind not in t.CIVILIAN_IDS and (str(name).casefold() not in t.CIVILIAN_NAMES) and (payload.get('amount', 1) > 0):
                self.all_production[owner][kind] += 1
        if action in ('STOP', 'DELETE'):
            for ident in ids:
                self.all_latest[ident] = -1
            return
        if action == 'AI_ORDER':
            target = payload.get('_troop_ai_target')
            if not target:
                self.all_ai_ignored[owner] += 1
                return
            x, y = target
        elif action in ('MOVE', 'PATROL', 'DE_ATTACK_MOVE') or (action == 'ORDER' and payload.get('target_id') in (-1, 4294967295)):
            x, y = (payload.get('x'), payload.get('y'))
        else:
            return
        if not self.valid_destination(x, y):
            return
        if not ids:
            self.all_omitted[owner] += 1
            return
        self.all_serial += 1
        members = []
        for ident in ids:
            obj = self.all_objects.get(ident)
            origin = self.all_refs.get(ident)
            if origin is None and obj and self.valid_destination(obj['x'], obj['y']):
                origin = (obj['x'], obj['y'], 'initial')
            self.all_refs[ident] = (x, y, 'previous_target')
            self.all_latest[ident] = self.all_serial
            if obj and (obj['kind'] != 'unit' or obj['type_id'] in t.CIVILIAN_IDS or str(obj['name']).casefold() in t.CIVILIAN_NAMES):
                continue
            members.append({'id': ident, 'type_id': obj['type_id'] if obj else None, 'name': obj['name'] if obj else 'Tipo desconhecido', 'origin': origin})
        if members:
            self.all_moves.append(dict(player=owner, serial=self.all_serial, ms=self.ms, destination=[x, y], members=members, action=action))

    def all_movements(self, players, horizon=60000, limit=3):
        result = []
        per_player = Counter()
        for event in reversed(self.all_moves):
            owner = event['player']
            if owner not in players or per_player[owner] >= limit or event['ms'] < self.ms - horizon:
                continue
            groups = {}
            for member in event['members']:
                if self.all_latest.get(member['id']) != event['serial']:
                    continue
                key = member['type_id']
                group = groups.setdefault(key, dict(type_id=key, name=member['name'], count=0, origins=[]))
                group['count'] += 1
                if member['origin'] is not None:
                    group['origins'].append(member['origin'])
            if not groups:
                continue
            for group in groups.values():
                origins = group.pop('origins')
                group['origin_count'] = len(origins)
                group['origin'] = [sum((a[0] for a in origins)) / len(origins), sum((a[1] for a in origins)) / len(origins)] if origins else None
                group['origin_sources'] = sorted({a[2] for a in origins})
            result.append(dict(player=owner, ms=event['ms'], destination=event['destination'], groups=list(groups.values()), action=event['action']))
            per_player[owner] += 1
        return result

    def movements(self, horizon=60000, limit=3):
        return self.all_movements(selected_ids(self), horizon, limit)
p.OrderSession = AllSession

def prepare_units(session):
    from unidades_034 import preparar
    preparar(session, globals())
t.ICONS.prepare = prepare_units
RESEARCH_META = {}

def prepare_research(session):
    prepare_units(session)
    for player in session.model['players']:
        owner = player['slot']
        name = re.sub('[^A-Za-z]', '', str(player['civilization'])).upper()
        tech = {}
        buildings = {}
        for civ in ('BRITONS', name):
            path = t.ROOT / 'icones_aoe2' / f'unidades_{civ}.json'
            try:
                document = json.loads(path.read_text('utf-8'))
                buildings.update({b['node_id']: b for b in document['buildings']})
                nodes = document['units_techs']
                if isinstance(nodes, dict):
                    nodes = nodes.values()
                tech.update({node['node_id']: node for node in nodes if node.get('use_type') == 'Tech'})
            except (OSError, ValueError, KeyError):
                pass
        RESEARCH_META[owner] = (tech, buildings)
    for record in records_all(session):
        tech, buildings = RESEARCH_META.get(record['player'], ({}, {}))
        node = tech.get(record['id'])
        site = buildings.get(record['building'])
        if node:
            m.RESEARCH.ensure('tech', record['id'], node['picture_index'], 'Tech')
        if site:
            m.RESEARCH.ensure('building', record['building'], site['picture_index'], 'Building')

def records_all(session):
    result = []
    for event in session.research.values():
        owner = event.get('player')
        if owner not in session.all_players:
            continue
        tech, _ = RESEARCH_META.get(owner, ({}, {}))
        ident = event.get('technology_id')
        site = tech.get(ident, {}).get('building_id')
        for obj_id in event.get('object_ids', []):
            obj = session.objects.get(obj_id)
            if obj and obj['kind'] == 'building':
                site = obj['type_id']
                break
        result.append(dict(player=owner, id=ident, name=event['name'], building=site, ms=event['ms'], requests=event['requests'], status='requested_not_completed'))
    return sorted(result, key=lambda a: (a['ms'], a['id']))
m.RESEARCH.prepare = prepare_research
m.RESEARCH.records = records_all

def entries(state):
    counts = state.get('building_counts')
    if not isinstance(counts, dict):
        return ()
    return tuple(sorted(((int(key), value) for key, value in counts.items() if isinstance(value, int) and (not isinstance(value, bool)) and (value > 0) and (int(key) in p.BUILDING_CATALOG))))
p.building_entries = entries

def world_state(session):
    from painel_tabela_036 import nomes_jogadores
    selected, revision = selection()
    players = selected_ids(session)
    research = records_all(session)
    colors = {a['number']: a['color_id'] for a in session.header.get('de', {}).get('players', []) if a.get('number', -1) > 0 and 0 <= a.get('color_id', -1) < 8}
    data = []
    for owner in players:
        data.append(dict(player=owner, game_ms=session.ms, building_counts=dict(session.all_buildings[owner]), military_orders={key: value for key, value in session.all_production[owner].items() if t.ICONS.military(key)}, research_orders=[record for record in research if record['player'] == owner], troop_movements=session.all_movements([owner], t.OPTIONS[2] * 1000, 3), color=mini.PLAYER_COLORS[colors.get(owner, (owner - 1) % 8)], selection_omitted=session.all_omitted[owner]))
    return nomes_jogadores(dict(player=selected, filter_revision=revision, game_ms=session.ms, per_player=data, roster=roster(session), source='recorded_orders_not_live_counts'), session)
p.order_state = world_state

def world_report(state):
    label = 'Todos os jogadores' if state['player'] == 0 else f"Jogador {state['player']}"
    lines = [f'FILTRO: {label}', f"Registros até {app.base.game_time(state['game_ms'])}", 'CONTADORES = PEDIDOS; não são quantidades vivas.', 'Pesquisas não indicam conclusão. R = referência, não partida confirmada.', 'Tipos identificados vêm do estado inicial; alterações posteriores não são confirmadas.', 'Tipo desconhecido pode incluir civis. Pedidos de produção não identificam instâncias novas.', 'Paliçadas mostram estado inicial/pedidos; bolinhas não comprovam falhas nem fechamento.', '']
    for data in state['per_player']:
        lines.append(f"JOGADOR {data['player']}")
        for ident, count in entries(data):
            lines.append(f'  {p.BUILDING_CATALOG[ident][0]}: {count} pedido(s)')
        for ident, count in data['military_orders'].items():
            lines.append(f"  {t.ICONS.data[ident]['name']}: {count} comando(s) de produção")
        for record in data['research_orders']:
            lines.append(f"  {app.base.game_time(record['ms'])} | {record['name']}: pesquisa solicitada")
        for event in data['troop_movements']:
            detail = ', '.join((f"{group['count']} {group['name']}" for group in event['groups']))
            lines.append(f"  {app.base.game_time(event['ms'])} → {event['destination']}: {detail}")
        lines.append(f"  Ordens sem seleção reconstruída: {data['selection_omitted']}")
    lines.extend(t.ICONS.errors[-2:])
    lines.extend(m.RESEARCH.errors[-2:])
    return '\n'.join(lines)
p.state_report = world_report
_base_walls = m.wall_geometry

def filtered_walls(session):
    original = getattr(session, '_full_session', session)
    wanted = selected_ids(original)
    edges, ends = _base_walls(original)
    return ([a for a in edges if a[0][0] in wanted], [a for a in ends if a[0] in wanted])
m.wall_geometry = filtered_walls
_base_map = app.map_svg

def selected_map(session):
    wanted = selected_ids(session)
    proxy = copy.copy(session)
    proxy._full_session = session
    proxy.model = dict(session.model)
    proxy.model['points'] = [a for a in session.model['points'] if a['kind'] != 'centros' or a['owner'] in wanted]
    proxy.initial = [a for a in session.initial if a['owner'] in wanted]
    proxy.build_requests = [a for a in session.build_requests if a.get('player') in wanted]
    proxy.movements = lambda *args, **kwargs: []
    root = ET.fromstring(_base_map(proxy))
    if not t.OPTIONS[0]:
        return ET.tostring(root, encoding='unicode')
    layer = root.find('{' + NS + '}g[@clip-path="url(#map-area)"]')
    defs = root.find('{' + NS + '}defs')
    if layer is None or defs is None:
        return ET.tostring(root, encoding='unicode')
    labels = ET.SubElement(root, '{' + NS + '}g')
    options = t._projection_context.options or mini.SETTINGS[:2]

    def add(parent, tag, **attrs):
        return ET.SubElement(parent, '{' + NS + '}' + tag, {key: str(value) for key, value in attrs.items()})

    def point(coords):
        return t._projection(coords[0], coords[1], session.model['dimension'], options[0], options[1])
    colors = {a['number']: a['color_id'] for a in session.header.get('de', {}).get('players', []) if a.get('number', -1) > 0 and 0 <= a.get('color_id', -1) < 8}
    embedded = set()
    arrows = set()
    size = t.OPTIONS[3]
    for event in session.all_movements(wanted, t.OPTIONS[2] * 1000, 3):
        owner = event['player']
        color = mini.PLAYER_COLORS[colors.get(owner, (owner - 1) % 8)]
        arrow = f'all-arrow-{owner}'
        if owner not in arrows:
            node = add(defs, 'marker', id=arrow, viewBox='0 0 10 10', refX=9, refY=5, markerWidth=5, markerHeight=5, orient='auto')
            add(node, 'path', d='M0 0L10 5L0 10Z', fill=color)
            arrows.add(owner)
        tx, ty = point(event['destination'])
        add(layer, 'circle', cx=tx, cy=ty, r=3, fill='none', stroke=color)
        groups = event['groups']
        step = size + 20
        start = min(890 - len(groups) * step, max(10, tx - len(groups) * step / 2))
        yy = min(430 - size, max(12, ty - size - 12))
        add(labels, 'text', x=start, y=yy - 3, fill=color, **{'font-size': 11, 'font-weight': 'bold'}).text = f'J{owner}'
        for index, group in enumerate(groups):
            if group['origin'] is not None:
                ox, oy = point(group['origin'])
                add(layer, 'line', x1=ox, y1=oy, x2=tx, y2=ty, stroke=color, **{'stroke-width': 1.5, 'stroke-dasharray': '4 3', 'marker-end': 'url(#' + arrow + ')'})
                add(layer, 'text', x=ox + 3, y=oy - 3, fill=color, **{'font-size': 10}).text = 'R'
            x = start + index * step
            ident = group['type_id']
            data = t.ICONS.images.get(ident)
            if data:
                key = f'all-unit-{ident}'
                if ident not in embedded:
                    add(defs, 'image', id=key, width=48, height=48, href='data:image/png;base64,' + base64.b64encode(data).decode())
                    embedded.add(ident)
                node = add(labels, 'g', transform=f'translate({x} {yy}) scale({size / 48})')
                add(node, 'use', href='#' + key)
            else:
                add(labels, 'text', x=x + size / 2, y=yy + size, fill='white', **{'font-size': size, 'text-anchor': 'middle'}).text = '?'
            add(labels, 'text', x=x + size + 2, y=yy + size * 0.85, fill='white', **{'font-size': 12, 'font-weight': 'bold'}).text = str(group['count'])
    return ET.tostring(root, encoding='unicode')
app.map_svg = selected_map
mini.minimap_svg = selected_map
ACTIONS = [('all', 'Todos', 0)] + [(f'player_{i}', f'Jogador {i}', i) for i in range(1, 9)] + [('previous', 'Jogador anterior', -1), ('next', 'Próximo jogador', -2)]
DEFAULT_KEYS = {'all': 'Ctrl+Alt+0', 'previous': 'Ctrl+Alt+Left', 'next': 'Ctrl+Alt+Right', **{f'player_{i}': f'Ctrl+Alt+{i}' for i in range(1, 9)}}
KEY_NAMES = {'LEFT': 37, 'RIGHT': 39, 'UP': 38, 'DOWN': 40, 'SPACE': 32, 'HOME': 36, 'END': 35, 'PGUP': 33, 'PGDN': 34, 'INSERT': 45, 'DELETE': 46}

def parse_key(value):
    if not isinstance(value, str):
        raise ValueError('Atalho deve ser texto.')
    if not value.strip():
        return None
    parts = [a.strip().upper() for a in value.split('+')]
    if len(parts) < 2 or any((not a for a in parts)):
        raise ValueError('Use modificador + tecla, por exemplo Ctrl+Alt+1.')
    modifiers = {'CTRL': 2, 'ALT': 1, 'SHIFT': 4, 'WIN': 8}
    mask = 0
    for part in parts[:-1]:
        if part not in modifiers or mask & modifiers[part]:
            raise ValueError('Modificador inválido ou repetido.')
        mask |= modifiers[part]
    key = parts[-1]
    if len(key) == 1 and key.isascii() and key.isalnum():
        vk = ord(key)
    elif key in KEY_NAMES:
        vk = KEY_NAMES[key]
    elif re.fullmatch('F([1-9]|1[0-9]|2[0-4])', key):
        vk = 112 + int(key[1:]) - 1
    else:
        raise ValueError('Tecla não reconhecida: ' + key)
    return (mask, vk)

def validate_keys(spec):
    used = set()
    result = {}
    for action, label, target in ACTIONS:
        chord = parse_key(spec.get(action, ''))
        if chord == (3, ord('M')):
            raise ValueError('Ctrl+Alt+M está reservado ao minimapa.')
        if chord is not None and chord in used:
            raise ValueError('Dois comandos usam o mesmo atalho.')
        if chord is not None:
            used.add(chord)
        result[action] = chord
    return result
if hasattr(p, 'CONFIG_DEFAULTS'):
    p.CONFIG_DEFAULTS.update(display_player='Todos', **{'key_' + key: value for key, value in DEFAULT_KEYS.items()})
    _validate = p._validate_config

    def validate_settings(values):
        result = _validate(values)
        allowed = ['Todos'] + [f'Jogador {i}' for i in range(1, 9)]
        if result['display_player'] not in allowed:
            raise ValueError('Jogador inválido.')
        validate_keys({key: result['key_' + key] for key in DEFAULT_KEYS})
        return result
    p._validate_config = validate_settings

class FilterQueue(queue.Queue):

    def __init__(self, window):
        super().__init__()
        self.window = window

    def get_nowait(self):
        result = super().get_nowait()
        epoch, kind, session, data = result
        window = self.window
        if epoch == window.epoch and kind == 'ok':
            window.update_roster(session)
            state = data['bar_state']
            if (state['player'], state['filter_revision']) != SELECTION:
                window.session = session
                return (epoch - 1, 'stale', session, None)
            window.bar_state = state
            window.caption_text = data.get('subtitle', '')
        return result

class Window(m.Window):

    def setup_position_controls(self, parent):
        super().setup_position_controls(parent)
        self._selection_ready = False
        self.display_player = tk.StringVar(value='Todos')
        for key, value in DEFAULT_KEYS.items():
            setattr(self, 'key_' + key, tk.StringVar(value=value))
        box = ttk.LabelFrame(parent, text='Jogadores e atalhos globais', padding=8)
        box.pack(fill='x', pady=6, before=self.report)
        row = ttk.Frame(box)
        row.pack(fill='x')
        self.shortcuts_status = tk.StringVar(value='Configurando atalhos…')
        self.player_box = ttk.Combobox(row, textvariable=self.display_player, state='readonly', values=['Todos'] + [f'Jogador {i}' for i in range(1, 9)], width=18)
        self.player_box.pack(side='left', padx=4)
        ttk.Button(row, text='Configurar atalhos…', command=self.keys_dialog).pack(side='left', padx=8)
        ttk.Label(row, text='A seleção filtra o minimapa e a barra. Recursos permanecem visíveis.').pack(side='left', padx=6)
        ttk.Label(box, textvariable=self.shortcuts_status, wraplength=820).pack(anchor='w', pady=(4, 0))
        self.display_player.trace_add('write', self.change_player)

    def __init__(self, root, native):
        self.key_commands = queue.Queue()
        self.key_events = queue.Queue()
        self.keys_stop = threading.Event()
        self.keys_token = 0
        self.pending_save = None
        self.players = []
        super().__init__(root, native)
        self.queue = FilterQueue(self)
        self._selection_ready = True
        self.change_player()
        threading.Thread(target=self.keys_worker, daemon=True).start()
        self.apply_keys()
        root.title('AoE2 — todos os jogadores · filtro e atalhos')
        self.relabel(self.report.master)

    def relabel(self, parent):
        for widget in parent.winfo_children():
            if isinstance(widget, (ttk.Label, ttk.LabelFrame)):
                text = str(widget.cget('text'))
                if 'jogador 2' in text:
                    widget.configure(text=text.replace('jogador 2', 'jogador selecionado'))
            if isinstance(widget, (ttk.Frame, ttk.LabelFrame)):
                self.relabel(widget)

    def change_player(self, *args):
        global SELECTION
        if not self._selection_ready:
            return
        value = self.display_player.get()
        owner = 0 if value == 'Todos' else int(value.split()[-1])
        if owner == SELECTION[0]:
            return
        SELECTION = (owner, SELECTION[1] + 1)
        self.next_frame = 0
        self.bar_cache = None
        self.photo = None
        self.image.configure(image='')
        self.overlay.withdraw()
        self.caption.withdraw()
        self.status.set('Filtro: ' + value + '. Atualizando a partir dos registros lidos…')

    def update_roster(self, session):
        self.players = roster(session)
        self.player_box.configure(values=['Todos'] + [f'Jogador {i}' for i in self.players])
        if SELECTION[0] and SELECTION[0] not in self.players:
            self.display_player.set('Todos')

    def attach(self, path):
        self.players = []
        self.player_box.configure(values=['Todos'] + [f'Jogador {i}' for i in range(1, 9)])
        super().attach(path)

    def choose(self, target):
        if target in (-1, -2):
            values = [0] + (self.players or list(range(1, 9)))
            current = SELECTION[0]
            index = values.index(current) if current in values else 0
            target = values[(index + (-1 if target == -1 else 1)) % len(values)]
        if target and self.players and (target not in self.players):
            self.status.set(f'Jogador {target} não existe nesta gravação.')
            return
        self.display_player.set('Todos' if target == 0 else f'Jogador {target}')

    def job(self, *args):
        CONTEXT.selection = SELECTION
        try:
            return super().job(*args)
        finally:
            del CONTEXT.selection

    def keys_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title('Atalhos para selecionar jogadores')
        for row, (key, label, target) in enumerate(ACTIONS):
            ttk.Label(dialog, text=label).grid(row=row, column=0, padx=12, pady=4, sticky='w')
            ttk.Entry(dialog, textvariable=getattr(self, 'key_' + key), width=30).grid(row=row, column=1, padx=12, pady=4)
        ttk.Label(dialog, text='Exemplos: Ctrl+Alt+1, Shift+F2, Ctrl+Right.\nCampo vazio desativa o atalho. Ctrl+Alt+M é reservado.').grid(row=len(ACTIONS), column=0, columnspan=2, padx=12, pady=10)
        ttk.Button(dialog, text='Aplicar atalhos', command=self.apply_keys).grid(row=len(ACTIONS) + 1, column=0, pady=10)
        ttk.Button(dialog, text='Salvar configurações', command=self.save_settings).grid(row=len(ACTIONS) + 1, column=1, pady=10)

    def key_spec(self):
        return {key: getattr(self, 'key_' + key).get() for key in DEFAULT_KEYS}

    def apply_keys(self, save=False):
        try:
            spec = validate_keys(self.key_spec())
        except ValueError as exc:
            message = 'Atalhos não aplicados: ' + str(exc)
            self.status.set(message)
            self.shortcuts_status.set(message)
            return
        self.keys_token += 1
        if save:
            self.pending_save = (self.keys_token, spec)
        self.key_commands.put((self.keys_token, spec))

    def keys_worker(self):
        active = {}
        user32 = self.native.u

        def unregister(mapping):
            for action in mapping:
                ident = 1000 + list(DEFAULT_KEYS).index(action)
                user32.UnregisterHotKey(None, ident)

        def register(spec):
            done = {}
            for action, chord in spec.items():
                if chord is None:
                    continue
                ident = 1000 + list(DEFAULT_KEYS).index(action)
                if not user32.RegisterHotKey(None, ident, chord[0] | 16384, chord[1]):
                    unregister(done)
                    return (False, {}, action)
                done[action] = chord
            return (True, done, None)
        try:
            while not self.keys_stop.wait(0.03):
                while not self.key_commands.empty():
                    token, spec = self.key_commands.get_nowait()
                    old = dict(active)
                    unregister(active)
                    ok, active, failed = register(spec)
                    if not ok:
                        restored, active, _ = register(old)
                        if restored:
                            detail = 'Atalhos anteriores mantidos.' if old else 'Nenhum atalho de seleção ativo; ajuste e aplique novamente.'
                        else:
                            detail = 'Restauração dos atalhos falhou.'
                        message = f'Atalho ocupado ou indisponível: {failed}. {detail}'
                    else:
                        message = 'Atalhos aplicados.'
                    self.key_events.put(('keys', token, ok, message, spec))
                msg = t.app.base.W.MSG()
                while user32.PeekMessageW(t.app.base.C.byref(msg), None, 786, 786, 1):
                    index = int(msg.wParam) - 1000
                    if 0 <= index < len(DEFAULT_KEYS):
                        action = list(DEFAULT_KEYS)[index]
                        target = next((a[2] for a in ACTIONS if a[0] == action))
                        self.key_events.put(('choose', target))
        finally:
            unregister(active)

    def save_settings(self):
        try:
            p._validate_config({key: getattr(self, key).get() for key in p.CONFIG_DEFAULTS})
        except (ValueError, tk.TclError) as exc:
            self.status.set('Configurações não salvas: ' + str(exc))
            return
        self.apply_keys(save=True)

    def apply_settings(self, values):
        warning = super().apply_settings(values)
        if self._selection_ready:
            self.apply_keys()
        return warning

    def rows(self):
        rows = []
        for data in self.bar_state.get('per_player', []):
            for kind, ident, count, techs in m.research_rows(data, self.troops_bar.get(), self.research_icons.get()):
                path = self.icon_path(kind, ident)
                if path is not None and path.is_file():
                    known_techs = tuple(((tech, amount) for tech, amount in techs if self.icon_path('tech', tech) is not None and self.icon_path('tech', tech).is_file()))
                    rows.append((data['player'], data['color'], kind, ident, count, known_techs))
        return rows

    def icon_path(self, kind, ident):
        path = m.RESEARCH.paths.get((kind, ident))
        if path is None and kind in ('building', 'unit'):
            filename = f'building_{ident}.png' if kind == 'building' else f'troop_{ident}.png'
            path = t.ROOT / 'icones_aoe2' / filename
        return path

    def photo_icon(self, kind, ident, x, y, size):
        key = (kind, ident, int(size))
        if key not in self._player_photos:
            try:
                raw = tk.PhotoImage(master=self.root, file=str(self.icon_path(kind, ident)))
                ratio = Fraction(max(1, int(size)), max(raw.width(), raw.height()))
                self._player_photos[key] = raw.zoom(ratio.numerator).subsample(ratio.denominator)
            except (OSError, tk.TclError):
                self._player_photos[key] = None
        image = self._player_photos[key]
        if image:
            self.canvas.create_image(x + size / 2, y + size / 2, image=image)

    def paint_bar(self, rows, size):
        self.canvas.delete('all')
        if getattr(self, '_player_photo_size', None) != size:
            self._player_photos = {}
            self._player_photo_size = size
        pad = max(3, round(size * 0.12))
        head = max(12, round(size * 0.3))
        yy = pad + head
        label = 'TODOS' if SELECTION[0] == 0 else f'J{SELECTION[0]}'
        self.canvas.create_text(pad, pad, text=label + ' · PEDIDOS', anchor='nw', fill='white', font=('Segoe UI', max(8, int(size * 0.2)), 'bold'))
        last = None
        maxtech = max((len(a[5]) for a in rows), default=0)
        width = math.ceil(pad * 2 + size * 2.5 + maxtech * size * 0.65)
        for owner, color, kind, ident, count, techs in rows:
            if owner != last:
                self.canvas.create_text(pad, yy, text=f'J{owner}', fill=color, anchor='nw', font=('Segoe UI', max(8, int(size * 0.25)), 'bold'))
                yy += size * 0.4
                last = owner
            self.photo_icon(kind, ident, pad, yy, size)
            if count is not None:
                self.canvas.create_text(pad + size * 1.6, yy + size * 0.5, text=str(count), fill='white', font=('Segoe UI', max(9, int(size * 0.45)), 'bold'))
            for index, (tech, requests) in enumerate(techs):
                xx = pad + size * 2.4 + index * size * 0.65
                self.photo_icon('tech', tech, xx, yy + size * 0.25, size // 2)
                if requests > 1:
                    self.canvas.create_text(xx + size * 0.5, yy + size * 0.75, text=str(requests), anchor='se', fill='white', font=('Segoe UI', max(6, int(size * 0.16))))
            yy += size * 1.25
        height = math.ceil(yy + pad)
        self.canvas.configure(width=width, height=height)
        self.caption_size = (width, height)

    def tick(self):
        while not self.key_events.empty():
            event = self.key_events.get_nowait()
            if event[0] == 'choose':
                self.choose(event[1])
            else:
                _, token, ok, message, spec = event
                if token == self.keys_token:
                    self.status.set(message)
                    self.shortcuts_status.set(message)
                if self.pending_save and self.pending_save[0] == token:
                    self.pending_save = None
                    if ok:
                        try:
                            unchanged = validate_keys(self.key_spec()) == spec
                        except ValueError:
                            unchanged = False
                        if unchanged:
                            super().save_settings()
                        else:
                            self.status.set('Atalhos alterados durante a aplicação; salve novamente.')
        app.base.Window.tick(self)
        if not self.closing:
            self.update_horizontal_panel()

    def close(self):
        self.keys_stop.set()
        super().close()
from rotas_012 import ativar as _ativar_rotas_012
_ativar_rotas_012(globals())
from gaia_minimapa import ativar as _ativar_gaia_minimapa
_ativar_gaia_minimapa(globals())
from recursos_manuais import ativar as _ativar_recursos_manuais
_ativar_recursos_manuais(globals())
from painel_horizontal import ativar as _ativar_painel_horizontal
_ativar_painel_horizontal(globals())
from central_replay import ativar as _ativar_central_replay
_ativar_central_replay(globals())
from filtros_construcoes import ativar as _ativar_filtros_construcoes
_ativar_filtros_construcoes(globals())
from controles_camadas import ativar as _ativar_controles_029
_ativar_controles_029(globals())
from enquadramento_035 import ativar as _ativar_enquadramento_035
_ativar_enquadramento_035(globals())
from painel_movel import ativar as _ativar_painel_movel
_ativar_painel_movel(globals())
from savegame_auto import ativar as _ativar_savegame_auto_0419
_ativar_savegame_auto_0419(globals())
from layout_0420 import ativar as _ativar_layout_0420
_ativar_layout_0420(globals())
from cliente_github_0421 import ativar as _ativar_github_0421
_ativar_github_0421(globals())
if __name__ == '__main__':
    native = app.base.Native()
    root = tk.Tk()
    Window(root, native)
    root.mainloop()
