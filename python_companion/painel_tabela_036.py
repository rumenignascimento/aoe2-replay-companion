"""Tabela de pedidos por jogador, inspirada no painel de pontuação do jogo."""
from collections import OrderedDict
from tkinter import font as tkfont
PAPER = '#d4b68d'
INK = '#302014'
EDGE = '#695039'

def nomes_jogadores(state, session):
    names = {}
    for record in session.header.get('de', {}).get('players', []):
        owner = record.get('number')
        name = record.get('name', '')
        if isinstance(name, bytes):
            name = name.decode('utf-8', errors='replace')
        if isinstance(name, str):
            names[owner] = name.strip()
    for player in state.get('per_player', []):
        player['player_name'] = names.get(player['player'], '')
    return state

def columns(width):
    left = max(68, min(190, round(width * 0.21)))
    available = width - left - 8
    return (4, left, left + round(available * 0.29), left + round(available * 0.56), width - 4)

def _wrap(tokens, available):
    lines = []
    line = []
    x = 0
    for token in tokens:
        w = token['width']
        if line and x + w > available:
            lines.append(line)
            line = []
            x = 0
        line.append((token, x))
        x += w
    if line:
        lines.append(line)
    return lines

def panel_layout(rows, width, size, max_height, players=()):
    edges = columns(width)
    col_widths = [edges[i + 1] - edges[i] - 12 for i in range(1, 4)]
    size = min(size, max(10, min(col_widths[0], col_widths[1]) - 8), max(10, int((col_widths[2] - 15) / 1.5)))
    size = min(size, max(10, max_height - 115))
    size = max(10, size - size % 2)
    small = max(5, size // 2)
    header = 68
    footer = 18
    line_height = size + 21
    per_row = max(1, (max_height - header - footer - 8) // line_height)
    owners = OrderedDict(((p['player'], {'player': p['player'], 'name': p.get('player_name', ''), 'color': p.get('color', '#888888'), 'cells': [[], [], []]}) for p in players))
    for row in rows:
        owner, color, kind, ident, count, techs = row
        data = owners.setdefault(owner, {'player': owner, 'name': '', 'color': color, 'cells': [[], [], []]})
        if kind in ('building', 'unit') and count is not None:
            index = 0 if kind == 'building' else 1
            token_width = min(col_widths[index], max(size + 10, len(str(count)) * 7 + 8))
            data['cells'][index].append({'kind': kind, 'id': ident, 'count': count, 'width': token_width})
        if techs:
            step = small + 8
            context = size + 7 if kind == 'building' else 0
            capacity = max(1, int((col_widths[2] - context) // step))
            for start in range(0, len(techs), capacity):
                selected = techs[start:start + capacity]
                data['cells'][2].append({'kind': 'research', 'producer': ident if kind == 'building' else None, 'techs': selected, 'width': context + len(selected) * step})
        elif kind == 'tech':
            data['cells'][2].append({'kind': 'research', 'producer': None, 'techs': ((ident, count),), 'width': small + 8})
    records = []
    for owner in owners.values():
        lines = [_wrap(tokens, available) for tokens, available in zip(owner['cells'], col_widths)]
        total_lines = max(1, *(len(a) for a in lines))
        for start in range(0, total_lines, per_row):
            portion = [column[start:start + per_row] for column in lines]
            height = max(1, *(len(a) for a in portion)) * line_height + 8
            records.append(dict(player=owner['player'], name=owner['name'], color=owner['color'], cells=portion, height=height, continuation=start > 0))
    pages = []
    current = []
    y = header
    for record in records:
        if current and y + record['height'] + footer > max_height:
            pages.append(dict(table_rows=current, height=y + footer, edges=edges, icon_size=size, line_height=line_height))
            current = []
            y = header
        current.append(dict(record, y=y))
        y += record['height']
    pages.append(dict(table_rows=current, height=max(header + 45, y + footer), edges=edges, icon_size=size, line_height=line_height))
    return pages

def paint(window, page, width, size, index, total):
    canvas = window.canvas
    canvas.delete('all')
    height = page['height']
    size = page['icon_size']
    small = size // 2
    body = getattr(window, 'body_font', 'Segoe UI')
    canvas.configure(width=width, height=height, bg=PAPER)
    canvas.create_rectangle(0, 0, width, height, fill=PAPER, outline=EDGE, width=2)
    canvas.create_rectangle(2, 2, width - 3, height - 3, outline='#ead3ad', width=1)
    for y in range(4, 67):
        f = (y - 4) / 63
        rgb = tuple((round(a + (b - a) * f) for a, b in zip((228, 205, 165), (197, 159, 115))))
        canvas.create_line(4, y, width - 5, y, fill='#%02x%02x%02x' % rgb)

    def tr(value):
        try:
            from idiomas_app import tr as translate
            return translate(value)
        except ImportError:
            return value

    def fit(text, available, font):
        if font.measure(text) <= available:
            return text
        while text and font.measure(text + '…') > available:
            text = text[:-1]
        return text + '…' if text else '…'
    font_px = max(9, min(16, round(size * 0.36)))
    normal = tkfont.Font(root=window.root, family=body, size=-font_px)
    bold = tkfont.Font(root=window.root, family=body, size=-font_px, weight='bold')
    tabs = ('Economia', 'Militar')
    tab_width = max(72, min(112, (width - 16) // 3))
    for i, tab in enumerate(tabs):
        x = 8 + i * (tab_width + 4)
        active = window.panel_tab.get() == tab
        hover = getattr(window, '_click_tab_hover', None) == tab
        pressed = getattr(window, '_click_tab_pressed', None) == tab
        fill = '#674323' if active else '#e7cca0'
        if hover:
            fill = '#75512f' if active else '#f1dcb8'
        if pressed:
            fill = '#50331c'
        y = 6 + (1 if pressed else 0)
        canvas.create_rectangle(x + 1, 8, x + tab_width + 2, 32, fill='#7a5a39', outline='', width=0)
        canvas.create_rectangle(x, y, x + tab_width, y + 23, fill=fill, outline='#65472b', width=1)
        inset = active or pressed
        top = '#3d2918' if inset else '#fff1cc'
        bottom = '#dab77e' if inset else '#805a33'
        canvas.create_line(x + 1, y + 1, x + tab_width - 1, y + 1, fill=top, width=1)
        canvas.create_line(x + 1, y + 1, x + 1, y + 22, fill=top, width=1)
        canvas.create_line(x + 1, y + 22, x + tab_width - 1, y + 22, fill=bottom, width=1)
        canvas.create_line(x + tab_width - 1, y + 1, x + tab_width - 1, y + 22, fill=bottom, width=1)
        tab_font = tkfont.Font(root=window.root, family=body, size=-max(10, min(16, font_px)), weight='bold')
        canvas.create_text(x + tab_width / 2, y + 11.5, text=fit(tr(tab), tab_width - 12, tab_font), fill='#fff3d5' if active or pressed else '#2f1f12', font=tab_font)
    if width >= 500:
        canvas.create_text(width - 10, 18, anchor='e', text=tr(f'PEDIDOS · página {index + 1}/{total}'), fill=INK, font=normal)
    edges = page['edges']
    for i, label in enumerate(('Jogador', 'Construções', 'Produção militar', 'Pesquisas e eras')):
        available = edges[i + 1] - edges[i] - 10
        canvas.create_text(edges[i] + 6, 49, text=fit(tr(label), available, bold), anchor='w', fill=INK, font=bold)
    canvas.create_line(4, 66, width - 5, 66, fill=EDGE)
    for number, row in enumerate(page['table_rows']):
        y = row['y']
        bottom = y + row['height']
        canvas.create_rectangle(4, y, width - 5, bottom, fill='#d8bb95' if number % 2 == 0 else '#c8a67e', outline='')
        canvas.create_line(4, bottom, width - 5, bottom, fill='#b89b76')
        for x in edges[1:-1]:
            canvas.create_line(x, y, x, bottom, fill='#b69a76')
        canvas.create_rectangle(9, y + 10, 27, y + 28, fill=row['color'], outline='#5b422a')
        color = row['color'].lstrip('#')
        try:
            r, g, b = (int(color[i:i + 2], 16) for i in (0, 2, 4))
            fg = 'black' if r * 0.299 + g * 0.587 + b * 0.114 > 155 else 'white'
        except ValueError:
            fg = 'white'
        canvas.create_text(18, y + 19, text=str(row['player']), fill=fg, font=bold)
        name = row['name'] or tr('Jogador ' + str(row['player']))
        label = fit(name, edges[1] - 39, bold)
        item = canvas.create_text(33, y + 18, text=label, anchor='w', fill=INK, font=bold)
        getattr(canvas.tk, 'raw', canvas.tk).call(str(canvas), 'itemconfigure', item, '-text', label)
        if row['continuation']:
            canvas.create_text(10, y + 40, text='↳', anchor='w', fill=INK, font=normal)
        for col, lines in enumerate(row['cells']):
            if not lines:
                canvas.create_text((edges[col + 1] + edges[col + 2]) / 2, y + 20, text='—', fill='#70563e', font=normal)
            for line_no, line in enumerate(lines):
                yy = y + 4 + line_no * page['line_height']
                for token, offset in line:
                    xx = edges[col + 1] + 6 + offset
                    if token['kind'] in ('building', 'unit'):
                        image = window.panel_photo(token['kind'], token['id'], size)
                        if image:
                            canvas.create_image(xx + token['width'] / 2, yy + size / 2, image=image)
                        digits = str(token['count'])
                        count_size = max(6, min(16, round(size * 0.36), int((token['width'] - 4) / (max(1, len(digits)) * 0.7))))
                        canvas.create_text(xx + token['width'] / 2, yy + size + 8, text=digits, fill=INK, font=(body, -count_size, 'bold'))
                    else:
                        if token['producer'] is not None:
                            image = window.panel_photo('building', token['producer'], size)
                            if image:
                                canvas.create_image(xx + size / 2, yy + size / 2, image=image)
                            xx += size + 7
                        for tech, amount in token['techs']:
                            image = window.panel_photo('tech', tech, small)
                            if image:
                                canvas.create_image(xx + small / 2, yy + size / 2, image=image)
                            if amount is not None and amount > 1:
                                canvas.create_text(xx + small / 2, yy + size + 6, text=str(amount), fill=INK, font=(body, -max(7, min(12, round(small * 0.6))), 'bold'))
                            xx += small + 8
    if not page['table_rows']:
        canvas.create_text(10, 86, text=tr('Sem pedidos identificáveis nesta aba.'), anchor='w', fill=INK, font=normal)
    if width < 500 or total > 1:
        canvas.create_text(width - 10, height - 9, anchor='e', text=f'{index + 1}/{total}', fill=INK, font=normal)
    window.caption_size = (width, height)
