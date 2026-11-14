import copy
from idiomas_app import fonte_interface as _fonte_interface
import io
import time
import tkinter as tk
from tkinter import ttk, font as tkfont
from PIL import Image, ImageChops, ImageDraw, ImageTk
BG = '#171a1a'
CARD = '#202424'
EDGE = '#514737'
TEXT = '#eee4d4'
MUTED = '#b8b6ac'
BRONZE = '#b88a4e'
CORNERS = ('Superior esquerdo', 'Superior direito', 'Inferior esquerdo', 'Inferior direito')

def ativar(g):
    if g.get('_central_replay_ativa'):
        return
    g['_central_replay_ativa'] = True
    p, mini, app = (g['p'], g['mini'], g['app'])
    p.CONFIG_DEFAULTS.update(central_buildings=True, central_icon_size=int(mini.MAP_ICON_SIZE))
    old_validate = p._validate_config

    def validate(values):
        result = old_validate(values)
        value = result['central_icon_size']
        if isinstance(value, bool) or not isinstance(value, int) or (not 6 <= value <= 48):
            raise ValueError('Ícones do minimapa: use um inteiro entre 6 e 48.')
        return result
    p._validate_config = validate
    layers = [True, int(mini.MAP_ICON_SIZE)]
    old_render = app.map_svg

    def render(session):
        buildings, size = getattr(g['CONTEXT'], 'central_layers', tuple(layers))
        proxy = session
        if not buildings:
            proxy = copy.copy(session)
            proxy.model = dict(session.model)
            proxy.model['points'] = [obj for obj in session.model['points'] if obj['kind'] != 'centros']
            proxy.initial = [obj for obj in session.initial if obj['kind'] != 'building']
            proxy.build_requests = []
            proxy._full_session = proxy
        previous = mini.MAP_ICON_SIZE
        mini.MAP_ICON_SIZE = size
        try:
            return old_render(proxy)
        finally:
            mini.MAP_ICON_SIZE = previous
    app.map_svg = render
    mini.minimap_svg = render
    g['selected_map'] = render
    old_frame = app.frame

    def frame(session, directory, width):
        data = old_frame(session, directory, 900)
        data['central_png'] = data['png']
        if width != 900:
            image = Image.open(io.BytesIO(data['png'])).convert('RGB')
            diff = ImageChops.difference(image, Image.new('RGB', image.size, (255, 0, 255)))
            a, b, c = diff.split()
            mask = ImageChops.lighter(ImageChops.lighter(a, b), c).point(lambda value: 255 if value else 0)
            image.putalpha(mask)
            image = image.resize((width, max(1, round(width / 2))), Image.Resampling.LANCZOS)
            opaque = Image.composite(image.convert('RGB'), Image.new('RGB', image.size, (255, 0, 255)), image.getchannel('A').point(lambda value: 255 if value >= 128 else 0))
            output = io.BytesIO()
            opaque.save(output, format='PNG')
            data['png'] = output.getvalue()
        return data
    app.frame = frame
    Base = g['Window']

    class Queue:

        def __init__(self, inner, window):
            self.inner = inner
            self.window = window

        def __getattr__(self, key):
            return getattr(self.inner, key)

        def get_nowait(self):
            result = self.inner.get_nowait()
            epoch, kind, session, data = result
            window = self.window
            if epoch == window.epoch and kind == 'ok':
                window.central_raw = data.get('central_png', data['png'])
                window.central_updated = time.monotonic()
                window.central_generation += 1
                window.central_map = session.model.get('map', 'Mapa')
                window.central_ms = session.ms
            return result

    class Window(Base):

        def __init__(self, root, native):
            self.central_buildings = tk.BooleanVar(master=root, value=True)
            self.central_icon_size = tk.IntVar(master=root, value=int(mini.MAP_ICON_SIZE))
            self._central_ready = False
            super().__init__(root, native)
            self.central_raw = None
            self.central_generation = 0
            self.central_updated = 0
            self.central_map = 'Nenhum replay aberto'
            self.central_ms = 0
            self.preview_key = None
            self.queue = Queue(self.queue, self)
            self.scroll_panels = []
            self.central_nav = 'Visão geral'
            self.central_buildings.trace_add('write', self.central_layers)
            self.central_icon_size.trace_add('write', self.central_layers)
            self.central_layers()
            for child in root.winfo_children():
                if not isinstance(child, (tk.Toplevel, tk.Menu)):
                    child.pack_forget()
                    child.grid_forget()
            self.theme()
            self.build_central()
            self._central_ready = True
            root.title('AoE II · Replay Companion')
            root.geometry(f'{min(1440, root.winfo_screenwidth() - 60)}x{min(920, root.winfo_screenheight() - 80)}')
            root.minsize(1000, 650)
            root.bind('<MouseWheel>', self.wheel)
            root.after(200, self.central_tick)

        def central_layers(self, *args):
            try:
                size = int(self.central_icon_size.get())
                if not 6 <= size <= 48:
                    return
                layers[:] = [bool(self.central_buildings.get()), size]
            except (ValueError, tk.TclError):
                return
            self.next_frame = 0

        def apply_settings(self, values):
            warning = super().apply_settings(values)
            self.central_layers()
            return warning

        def change_player(self, *args):
            previous = g['SELECTION']
            super().change_player(*args)
            if self._central_ready and previous != g['SELECTION']:
                self.central_raw = None
                self.preview_key = None

        def attach(self, *args, **kwargs):
            if self._central_ready:
                self.central_raw = None
                self.preview_key = None
            return super().attach(*args, **kwargs)

        def job(self, *args, **kwargs):
            g['CONTEXT'].central_layers = tuple(layers)
            try:
                return super().job(*args, **kwargs)
            finally:
                del g['CONTEXT'].central_layers

        def theme(self):
            families = {name.lower() for name in tkfont.families(self.root)}
            self.body_font = _fonte_interface('Segoe UI' if 'segoe ui' in families else 'Helvetica')
            self.title_font = _fonte_interface('Georgia' if 'georgia' in families else 'Palatino')
            self.code_font = 'Consolas' if 'consolas' in families else 'Courier'
            self.root.configure(bg=BG)
            style = ttk.Style(self.root)
            style.theme_use('clam')
            style.configure('.', background=CARD, foreground=TEXT, font=(self.body_font, 10))
            style.configure('TFrame', background=BG)
            style.configure('Card.TFrame', background=CARD)
            style.configure('TLabel', background=CARD, foreground=TEXT)
            style.configure('TButton', background='#34332c', foreground=TEXT, bordercolor=EDGE, lightcolor=EDGE, darkcolor=EDGE, focuscolor=BRONZE, padding=(10, 7))
            style.map('TButton', background=[('active', '#514432'), ('pressed', '#775735')])
            style.configure('Accent.TButton', background='#795a32', foreground='#fff0d8')
            style.configure('TEntry', fieldbackground='#282d2c', foreground=TEXT, insertcolor=TEXT)
            style.configure('TCombobox', fieldbackground='#282d2c', foreground=TEXT, arrowcolor=BRONZE)
            style.map('TCombobox', fieldbackground=[('readonly', '#282d2c')], foreground=[('readonly', TEXT)])
            style.configure('TSpinbox', fieldbackground='#282d2c', foreground=TEXT, arrowcolor=BRONZE)
            style.configure('TScale', background=CARD, troughcolor='#3b3e38')
            style.configure('TNotebook', background=CARD, borderwidth=0)
            style.configure('TNotebook.Tab', background='#2b2e2a', foreground=TEXT, padding=(14, 8))
            style.map('TNotebook.Tab', background=[('selected', '#795a32')])
            style.configure('TLabelframe', background=CARD, bordercolor=EDGE)
            style.configure('TLabelframe.Label', background=CARD, foreground=TEXT)
            self.toggle_images = []
            for selected in (False, True):
                image = Image.new('RGBA', (40, 22))
                draw = ImageDraw.Draw(image)
                draw.rounded_rectangle((0, 0, 39, 21), radius=11, fill=BRONZE if selected else '#555a54')
                x = 20 if selected else 2
                draw.ellipse((x, 2, x + 17, 19), fill='#f5ead5')
                self.toggle_images.append(ImageTk.PhotoImage(image, master=self.root))
            style.element_create('Replay.Toggle', 'image', self.toggle_images[0], ('selected', self.toggle_images[1]))
            style.layout('Switch.TCheckbutton', [('Checkbutton.padding', {'sticky': 'nswe', 'children': [('Replay.Toggle', {'side': 'left', 'sticky': 'w'}), ('Checkbutton.label', {'side': 'left', 'sticky': 'w'})]})])
            style.configure('Switch.TCheckbutton', background=CARD, foreground=TEXT, padding=5)
            from acabamento_visual import aplicar_tema
            aplicar_tema(self)

        def card(self, parent, title=None):
            box = tk.Frame(parent, bg=CARD, highlightbackground=EDGE, highlightthickness=1)
            if title:
                tk.Label(box, text=title, bg=CARD, fg=TEXT, font=(self.title_font, 16, 'bold'), anchor='w').pack(fill='x', padx=14, pady=(12, 8))
            return box

        def scrollbox(self, parent):
            shell = ttk.Frame(parent, style='Card.TFrame')
            shell.pack(fill='both', expand=True)
            canvas = tk.Canvas(shell, bg=CARD, highlightthickness=0)
            bar = ttk.Scrollbar(shell, orient='vertical', command=canvas.yview)
            canvas.configure(yscrollcommand=bar.set)
            bar.pack(side='right', fill='y')
            canvas.pack(side='left', fill='both', expand=True)
            body = ttk.Frame(canvas, style='Card.TFrame', padding=12)
            item = canvas.create_window(0, 0, window=body, anchor='nw')
            body.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas.bind('<Configure>', lambda event: canvas.itemconfigure(item, width=event.width))
            self.scroll_panels.append((shell, canvas))
            return body

        def wheel(self, event):
            widget = event.widget
            if widget.winfo_toplevel() != self.root:
                return
            for shell, canvas in self.scroll_panels:
                node = widget
                while node is not None:
                    if node == shell:
                        canvas.yview_scroll(-1 if event.delta > 0 else 1, 'units')
                        return 'break'
                    node = getattr(node, 'master', None)

        def field(self, parent, label, variable, values=None, bounds=None):
            row = ttk.Frame(parent, style='Card.TFrame')
            row.pack(fill='x', pady=6)
            ttk.Label(row, text=label).pack(anchor='w', pady=(0, 4))
            if values is not None:
                widget = ttk.Combobox(row, textvariable=variable, values=values, state='readonly')
            elif bounds:
                widget = ttk.Spinbox(row, textvariable=variable, from_=bounds[0], to=bounds[1], increment=1, command=self.refresh_central)
            else:
                widget = ttk.Entry(row, textvariable=variable)
            widget.pack(fill='x')
            widget.bind('<Return>', lambda event: self.refresh_central())
            widget.bind('<FocusOut>', lambda event: self.refresh_central())
            return widget

        def switch(self, parent, label, variable):
            ttk.Checkbutton(parent, text='  ' + label, variable=variable, style='Switch.TCheckbutton', command=self.refresh_central).pack(anchor='w', pady=3)

        def refresh_central(self, *args):
            self.next_frame = 0
            self.preview_key = None

        def build_central(self):
            shell = tk.Frame(self.root, bg=BG)
            shell.pack(fill='both', expand=True)
            top = tk.Frame(shell, bg='#202321', height=62)
            top.pack(fill='x')
            tk.Label(top, text='II', bg='#65372a', fg='#f3cd83', font=(self.title_font, 22, 'bold'), padx=12).pack(side='left', padx=(18, 12), pady=10)
            tk.Label(top, text='AoE II · Replay Companion', bg='#202321', fg=TEXT, font=(self.title_font, 19, 'bold')).pack(side='left')
            ttk.Button(top, text='Abrir replay', style='Primary.TButton', command=self.choose_file).pack(side='right', padx=16)
            ttk.Button(top, text='Pasta savegame', command=self.choose_folder).pack(side='right')
            self.monitor_label = tk.Label(top, bg='#202321', fg='#94be7d', text='● Sem monitoramento')
            self.monitor_label.pack(side='right', padx=16)
            foot = tk.Frame(shell, bg='#202321')
            foot.pack(side='bottom', fill='x')
            ttk.Button(foot, text='Alterar pasta', command=self.choose_folder).pack(side='right', padx=10, pady=6)
            tk.Label(foot, textvariable=self.status, bg='#202321', fg=MUTED, anchor='w', wraplength=1000).pack(side='left', padx=16, fill='x', expand=True)
            body = tk.Frame(shell, bg=BG)
            body.pack(fill='both', expand=True)
            side = tk.Frame(body, bg='#1e2221', width=180)
            side.pack(side='left', fill='y')
            side.pack_propagate(False)
            tk.Label(side, text='CENTRAL DE REPLAY', bg='#1e2221', fg=BRONZE, font=(self.body_font, 9, 'bold')).pack(anchor='w', padx=16, pady=20)
            self.nav_buttons = {}
            for name in ('Visão geral', 'Overlay', 'Minimapa', 'Ordens'):
                button = tk.Button(side, text=name, command=lambda n=name: self.navigate(n), bg='#1e2221', fg=TEXT, activebackground='#514432', activeforeground=TEXT, bd=0, highlightthickness=0, anchor='w', padx=18, pady=14, font=(self.body_font, 12))
                button.pack(fill='x', pady=2)
                self.nav_buttons[name] = button
            ttk.Button(side, text='Configurações', command=lambda: self.navigate('Configurações')).pack(side='bottom', fill='x', padx=12, pady=14)
            ttk.Button(side, text='Atalhos', command=self.keys_dialog).pack(side='bottom', fill='x', padx=12)
            right = self.card(body, 'Overlay')
            right.pack(side='right', fill='y', padx=(0, 16), pady=16)
            right.configure(width=290)
            right.pack_propagate(False)
            controls = self.scrollbox(right)
            self.switch(controls, 'Exibir overlay', self.show)
            tabs = ttk.Notebook(controls)
            tabs.pack(fill='x', pady=10)
            appearance = ttk.Frame(tabs, style='Card.TFrame', padding=8)
            position = ttk.Frame(tabs, style='Card.TFrame', padding=8)
            tabs.add(appearance, text='Aparência')
            tabs.add(position, text='Posição')
            self.field(appearance, 'Largura (px)', self.width, bounds=(300, 900))
            ttk.Scale(appearance, from_=300, to=900, variable=self.width, command=lambda value: self.resize()).pack(fill='x')
            ttk.Label(appearance, text='Opacidade').pack(anchor='w', pady=(12, 4))
            ttk.Scale(appearance, from_=0.2, to=1, variable=self.opacity, command=self.alpha).pack(fill='x')
            self.opacity_label = ttk.Label(appearance)
            self.opacity_label.pack(anchor='e')
            self.overlay_settings_tabs = tabs
            self.overlay_position_page = position
            position_targets = ttk.Notebook(position)
            position_targets.pack(fill='x', expand=True)
            map_position = ttk.Frame(position_targets, style='Card.TFrame', padding=6)
            panel_position = ttk.Frame(position_targets, style='Card.TFrame', padding=6)
            position_targets.add(map_position, text='Minimapa')
            position_targets.add(panel_position, text='Painel horizontal')
            self.position_target_tabs = position_targets
            self.position_minimap_page = map_position
            self.position_panel_page = panel_position
            self.setup_table_position_controls(panel_position)
            position_targets.bind('<<NotebookTabChanged>>', self.fit_position_notebooks, add='+')
            tabs.bind('<<NotebookTabChanged>>', self.fit_position_notebooks, add='+')
            self.fit_position_notebooks()
            self.field(map_position, 'Posição', self.position_corner, values=CORNERS)
            self.field(map_position, 'Margem X (px)', self.position_x, bounds=(0, 10000))
            self.add_position_slider(map_position, 'x')
            self.field(map_position, 'Margem Y (px)', self.position_y, bounds=(0, 10000))
            if hasattr(self, 'setup_minimap_fit_controls'):
                self.setup_minimap_fit_controls(map_position)
            self.add_position_slider(map_position, 'y')
            ttk.Button(controls, text='Testar por 10 segundos', style='Test.TButton', command=self.preview_position_target).pack(fill='x', pady=12)
            ttk.Label(controls, text='Ctrl + Alt + M\nExibir ou ocultar o overlay.', wraplength=230).pack(anchor='w', pady=8)
            ttk.Button(controls, text='Celular / tablet · QR Code', command=lambda: self.mobile_dialog()).pack(fill='x', pady=10)
            ttk.Button(controls, text='Salvar configurações', command=self.save_settings).pack(fill='x', pady=6)
            center = tk.Frame(body, bg=BG)
            center.pack(fill='both', expand=True, padx=16, pady=16)
            self.page_title = tk.Label(center, text='Visão geral', bg=BG, fg=TEXT, font=(self.title_font, 26, 'bold'), anchor='w')
            self.page_title.pack(fill='x')
            self.meta = tk.Label(center, text='Mapa inicial e ordens do replay.', bg=BG, fg=MUTED, anchor='w')
            self.meta.pack(fill='x', pady=(4, 12))
            self.overview = tk.Frame(center, bg=BG)
            self.map_card = self.card(self.overview)
            self.map_card.pack(fill='both', expand=True)
            heading = tk.Frame(self.map_card, bg=CARD)
            heading.pack(fill='x', padx=14, pady=10)
            tk.Label(heading, text='Prévia do minimapa', bg=CARD, fg=TEXT, font=(self.title_font, 16, 'bold')).pack(side='left')
            self.central_players = ttk.Combobox(heading, textvariable=self.display_player, state='readonly', width=17)
            self.central_players.pack(side='right')
            summary = tk.Frame(self.map_card, bg=CARD)
            summary.pack(side='bottom', fill='x', padx=12, pady=10)
            self.summary_labels = []
            for text in ('Construções', 'Produção', 'Pesquisas'):
                label = tk.Label(summary, text='0 ' + text, bg='#2a2f2b', fg=TEXT, pady=10, font=(self.body_font, 10))
                label.pack(side='left', fill='x', expand=True, padx=3)
                self.summary_labels.append(label)
            self.preview_canvas = tk.Canvas(self.map_card, bg='#181d1b', highlightthickness=0, height=300)
            self.preview_canvas.pack(fill='both', expand=True, padx=10)
            self.preview_canvas.bind('<Configure>', lambda event: setattr(self, 'preview_key', None))
            layer_card = self.card(self.overview, 'Camadas e informações')
            layer_card.pack(fill='x', pady=(12, 0))
            rows = ttk.Frame(layer_card, style='Card.TFrame')
            rows.pack(fill='x', padx=10, pady=(0, 10))
            left = ttk.Frame(rows, style='Card.TFrame')
            left.pack(side='left', expand=True, fill='x')
            other = ttk.Frame(rows, style='Card.TFrame')
            other.pack(side='left', expand=True, fill='x')
            self.switch(left, 'Terreno', self.map_terrain)
            self.switch(left, 'Deslocamentos', self.troops_map)
            self.switch(other, 'Construções', self.central_buildings)
            self.switch(other, 'Pesquisas e eras', self.research_icons)
            self.advanced = self.card(self.overview)
            self.advanced_body = self.scrollbox(self.advanced)
            self.orders_page = self.card(center, 'Ordens registradas')
            order_heading = ttk.Frame(self.orders_page, style='Card.TFrame', padding=10)
            order_heading.pack(fill='x')
            self.order_players = ttk.Combobox(order_heading, textvariable=self.display_player, state='readonly')
            self.order_players.pack(side='left')
            ttk.Button(order_heading, text='Abrir relatórios', command=self.open_output).pack(side='right')
            self.orders_text = tk.Text(self.orders_page, bg='#1b201e', fg=TEXT, insertbackground=TEXT, wrap='word', font=(self.code_font, 10), bd=0)
            bar = ttk.Scrollbar(self.orders_page, command=self.orders_text.yview)
            bar.pack(side='right', fill='y')
            self.orders_text.configure(yscrollcommand=bar.set)
            self.orders_text.pack(fill='both', expand=True, padx=10, pady=10)
            self.settings_page = self.card(center, 'Configurações')
            settings = self.scrollbox(self.settings_page)
            self.field(settings, 'Pasta savegame monitorada', self.folder).configure(state='readonly')
            for text, command in (('Alterar pasta / monitorar', self.choose_folder), ('Salvar configurações', self.save_settings), ('Restaurar configurações originais', self.restore_settings), ('Configurar atalhos de jogadores', self.keys_dialog), ('Conectar celular / tablet', lambda: self.mobile_dialog())):
                ttk.Button(settings, text=text, command=command).pack(anchor='w', pady=6)
            ttk.Label(settings, text='Os números representam pedidos registrados. Não confirmam conclusões, unidades vivas ou posições atuais.\nA atualização é contínua e aguarda o processamento anterior terminar.', wraplength=520).pack(anchor='w', pady=16)
            self.navigate('Visão geral')
            from ajuda_replay import instalar as instalar_ajuda
            instalar_ajuda(self, top, side)
            self.switch(other, 'Gaia', self.gaia_show)
            self.resource_controls()
            self.building_filter_controls(rows)
            from acabamento_visual import preparar_navegacao
            preparar_navegacao(self)
            _orientacao_mapa_042(self)
            _tamanhos_icones_043(self)

        def navigate(self, name):
            self.central_nav = name
            self.page_title.configure(text=name)
            for page in (self.overview, self.orders_page, self.settings_page, self.advanced):
                page.pack_forget()
            for key, button in self.nav_buttons.items():
                button.configure(bg='#5b452e' if key == name else '#1e2221')
            if name == 'Ordens':
                self.orders_page.pack(fill='both', expand=True)
            elif name == 'Configurações':
                self.settings_page.pack(fill='both', expand=True)
            else:
                self.overview.pack(fill='both', expand=True)
                if name in ('Minimapa', 'Overlay'):
                    self.advanced.pack(fill='x', pady=(10, 0))
                    self.advanced.configure(height=220)
                    self.advanced.pack_propagate(False)
                    for child in self.advanced_body.winfo_children():
                        child.destroy()
                    parent = self.advanced_body
                    if name == 'Minimapa':
                        self.field(parent, 'Intervalo visível das ordens (segundos)', self.troops_seconds, bounds=(5, 300))
                        self.switch(parent, 'Possíveis aberturas nas paliçadas', self.wall_endpoints)
                    else:
                        self.switch(parent, 'Exibir painel de pedidos', self.caption_show)
                        self.switch(parent, 'Produção militar no painel', self.troops_bar)
                        self.field(parent, 'Tamanho dos ícones do painel', self.bar_size, bounds=(24, 120))
                        ttk.Label(parent, text='Opacidade do painel').pack(anchor='w')
                        ttk.Scale(parent, from_=0.2, to=1, variable=self.bar_opacity).pack(fill='x')
            self.preview_key = None
            self.setup_horizontal_controls(name)
            from acabamento_visual import atualizar_navegacao
            atualizar_navegacao(self)

        def central_tick(self):
            if self.closing:
                return
            try:
                values = ['Todos'] + [f'Jogador {number}' for number in self.players]
                for widget in (self.central_players, self.order_players):
                    widget.configure(values=values)
                monitoring = bool(self.folder.get())
                self.monitor_label.configure(text='● Monitorando savegame' if monitoring else '● Abra um replay ou selecione a pasta', fg='#94be7d' if monitoring else MUTED)
                ago = int(time.monotonic() - self.central_updated) if self.central_updated else None
                self.meta.configure(text=f'{self.central_map}  ·  Replay até {app.base.game_time(self.central_ms)}' + (f'  ·  Atualizado há {ago}s' if ago is not None else ''))
                self.opacity_label.configure(text=f'{float(self.opacity.get()):.0%}')
                state = self.bar_state.get('per_player', [])
                totals = [sum((sum((int(value) for value in player.get('building_counts', {}).values())) for player in state)), sum((sum((int(value) for value in player.get('military_orders', {}).values())) for player in state)), sum((sum((int(record['requests']) for record in player.get('research_orders', []))) for player in state))]
                for label, count, name in zip(self.summary_labels, totals, ('construções', 'produção', 'pesquisas')):
                    label.configure(text=f'{count} pedidos · {name}')
                if getattr(self, 'orders_generation', None) != self.central_generation:
                    self.orders_generation = self.central_generation
                    self.orders_text.configure(state='normal')
                    self.orders_text.delete('1.0', 'end')
                    self.orders_text.insert('1.0', self.report.get('1.0', 'end'))
                    self.orders_text.configure(state='disabled')
                width = max(1, self.preview_canvas.winfo_width())
                height = max(1, self.preview_canvas.winfo_height())
                key = (self.central_generation, width, height, self.central_raw is not None)
                if key != self.preview_key:
                    self.preview_key = key
                    self.preview_canvas.delete('all')
                    if self.central_raw:
                        image = Image.open(io.BytesIO(self.central_raw)).convert('RGB')
                        diff = ImageChops.difference(image, Image.new('RGB', image.size, (255, 0, 255)))
                        a, b, c = diff.split()
                        mask = ImageChops.lighter(ImageChops.lighter(a, b), c).point(lambda value: 255 if value else 0)
                        image = Image.composite(image, Image.new('RGB', image.size, '#181d1b'), mask)
                        scale = min(max(1, width - 12) / image.width, max(1, height - 12) / image.height)
                        image = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.LANCZOS)
                        self.central_photo = ImageTk.PhotoImage(image, master=self.root)
                        self.preview_canvas.create_image(width / 2, height / 2, image=self.central_photo)
                    else:
                        self.preview_canvas.create_text(width / 2, height / 2, text='Abra um replay para visualizar o mapa\nou monitore a pasta savegame.', fill=MUTED, font=(self.body_font, 13), justify='center')
            except tk.TclError:
                if not self.root.winfo_exists():
                    return
            finally:
                if not self.closing:
                    self.root.after(200, self.central_tick)
    g['Window'] = Window

def _orientacao_mapa_042(window):
    import tkinter as tk
    from tkinter import ttk
    existing = getattr(window, '_orientation_toolbar_042', None)
    if existing is not None and existing.winfo_exists():
        return
    canvas = window.preview_canvas
    toolbar = ttk.Frame(canvas.master, style='Card.TFrame')
    toolbar.pack(fill='x', before=canvas, padx=10, pady=(0, 8))
    window._orientation_toolbar_042 = toolbar
    ttk.Label(toolbar, text='Rotação').pack(side='left', padx=(0, 6))
    combo = ttk.Combobox(toolbar, textvariable=window.map_turn, values=('0°', '90°', '180°', '270°'), state='readonly', width=7)
    combo.pack(side='left', padx=(0, 8))
    window._orientation_combo_042 = combo

    def update():
        if hasattr(window, 'map_options'):
            window.map_options()
        window.next_frame = 0
        if hasattr(window, 'refresh_central'):
            window.refresh_central()

    def rotate(step):
        try:
            angle = int(str(window.map_turn.get()).replace('°', '').strip())
        except (ValueError, tk.TclError):
            angle = 0
        window.map_turn.set(str((angle + step) % 360) + '°')
        update()
    combo.bind('<<ComboboxSelected>>', lambda event: update())
    window._orientation_left_042 = ttk.Button(toolbar, text='-90°', width=5, command=lambda: rotate(-90))
    window._orientation_left_042.pack(side='left', padx=(0, 4))
    window._orientation_right_042 = ttk.Button(toolbar, text='+90°', width=5, command=lambda: rotate(90))
    window._orientation_right_042.pack(side='left', padx=(0, 10))
    window._orientation_mirror_042 = ttk.Checkbutton(toolbar, text='Espelhar mapa', variable=window.map_mirror, command=update)
    window._orientation_mirror_042.pack(side='left')

def _tamanhos_icones_043(window):
    import tkinter as tk
    from tkinter import ttk
    existing = getattr(window, '_icon_sizes_toolbar_043', None)
    if existing is not None and existing.winfo_exists():
        return
    canvas = window.preview_canvas
    box = ttk.Frame(canvas.master, style='Card.TFrame')
    box.pack(fill='x', before=canvas, padx=10, pady=(0, 8))
    window._icon_sizes_toolbar_043 = box
    window._icon_size_scales_043 = {}
    window._icon_size_values_043 = {}
    window._icon_size_fields_043 = {}
    traces = []
    cells = []
    items = (('Gaia', 'gaia_icon_size', 6, 48, 'gaia_options'), ('Construções', 'central_icon_size', 6, 48, 'central_layers'), ('Unidades', 'troops_icon_size', 10, 40, 'troop_options'))

    def update(callback):
        function = getattr(window, callback, None)
        if function is not None:
            function()
        window.next_frame = 0
        if hasattr(window, 'refresh_central'):
            window.refresh_central()
    for label, name, low, high, callback in items:
        cell = ttk.Frame(box, style='Card.TFrame')
        cells.append(cell)
        cell.columnconfigure(1, weight=1)
        source = getattr(window, name)
        value = tk.DoubleVar(master=window.root, value=max(low, min(high, int(source.get()))))
        guard = [False]

        def from_field(*args, src=source, val=value, lock=guard, lo=low, hi=high, cb=callback):
            if lock[0]:
                return
            try:
                number = int(src.get())
            except (ValueError, tk.TclError):
                return
            if not lo <= number <= hi:
                return
            lock[0] = True
            try:
                val.set(number)
            finally:
                lock[0] = False
            update(cb)

        def from_slider(raw, src=source, val=value, lock=guard, lo=low, hi=high, cb=callback):
            if lock[0]:
                return
            number = max(lo, min(hi, round(float(raw))))
            lock[0] = True
            try:
                src.set(number)
                val.set(number)
            finally:
                lock[0] = False
            update(cb)
        ttk.Label(cell, text=label).grid(row=0, column=0, sticky='w', padx=(0, 5))
        field = ttk.Spinbox(cell, textvariable=source, from_=low, to=high, increment=1, width=4)
        field.grid(row=0, column=1, sticky='ew')
        slider = ttk.Scale(cell, from_=low, to=high, variable=value, command=from_slider)
        slider.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 0))
        window._icon_size_scales_043[name] = slider
        window._icon_size_values_043[name] = value
        window._icon_size_fields_043[name] = field
        traces.append((source, source.trace_add('write', from_field)))
    layout = [None]

    def reflow(event=None):
        needed = max((cell.winfo_reqwidth() + 12 for cell in cells)) * len(cells)
        columns = 3 if box.winfo_width() >= needed else 1
        if columns == layout[0]:
            return
        layout[0] = columns
        for column in range(3):
            box.columnconfigure(column, weight=1 if column < columns else 0, uniform='icon043' if column < columns else '')
        for index, cell in enumerate(cells):
            cell.grid(row=index // columns, column=index % columns, sticky='ew', padx=(0, 10) if columns == 3 and index < 2 else 0, pady=(0, 5))
    box.bind('<Configure>', reflow, add='+')
    window.root.after_idle(reflow)

    def cleanup(event):
        if event.widget is box:
            for variable, token in traces:
                try:
                    variable.trace_remove('write', token)
                except tk.TclError:
                    pass
    box.bind('<Destroy>', cleanup, add='+')
