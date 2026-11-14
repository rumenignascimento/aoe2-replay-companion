import copy
import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import ttk
HOUSES = {70, 191, 192, 463, 464, 465}
MILITARY = {12, 45, 49, 72, 79, 82, 87, 101, 103, 104, 117, 155, 209, 234, 235, 236, 487, 598, 792, 1251, 1665, 1806}
ECONOMIC = {50, 68, 71, 84, 109, 141, 142, 276, 562, 584, 621, 1021, 1734, 1754, 1808, 1889, 2556}
KEYS = ('hide_military_buildings', 'hide_economic_buildings', 'hide_houses')

def category(ident, reference):
    if ident in HOUSES:
        return 2
    if ident in MILITARY:
        return 0
    if ident in ECONOMIC:
        return 1
    name = str(reference.get('objects', {}).get(str(ident), '')).strip().casefold()
    if name.startswith('house'):
        return 2
    if any((word in name for word in ('barracks', 'archery range', 'stable', 'siege workshop', 'castle', 'krepost', 'donjon', 'monastery', 'church', 'blacksmith', 'university', 'tower', 'outpost', 'wall', 'gate', 'dock'))):
        return 0
    if any((word in name for word in ('town center', 'mill', 'market', 'lumber camp', 'mining camp', 'farm', 'folwark', 'feitoria', 'caravanserai', 'mule cart', 'pasture', 'settlement', 'wonder'))):
        return 1
    return None

def ativar(g):
    if g.get('_filtros_construcoes_ativos'):
        return
    g['_filtros_construcoes_ativos'] = True
    g['p'].CONFIG_DEFAULTS.update({key: False for key in KEYS})
    flags = [False, False, False]
    original = g['app'].map_svg
    ns = g['NS']

    def render(session):
        hidden = getattr(g['CONTEXT'], 'building_filters', tuple(flags))
        svg = original(session)
        if not any(hidden):
            return svg
        root = ET.fromstring(svg)
        for parent in list(root.iter()):
            for node in list(parent):
                ident = node.get('data-building-id')
                if ident is None:
                    continue
                try:
                    kind = category(int(ident), session.reference)
                except (ValueError, TypeError):
                    continue
                if kind is None or not hidden[kind]:
                    continue
                if node.get('data-kind') == 'initial':
                    for child in node:
                        if child.tag == '{' + ns + '}text' and (child.text or '').startswith('J'):
                            parent.append(copy.deepcopy(child))
                parent.remove(node)
        return ET.tostring(root, encoding='unicode')
    g['app'].map_svg = render
    g['mini'].minimap_svg = render
    g['selected_map'] = render
    Base = g['Window']

    class Window(Base):

        def __init__(self, root, native):
            for key in KEYS:
                setattr(self, key, tk.BooleanVar(master=root, value=False))
            super().__init__(root, native)
            for key in KEYS:
                getattr(self, key).trace_add('write', self.building_filter_options)
            self.building_filter_options()

        def building_filter_options(self, *args):
            flags[:] = [bool(getattr(self, key).get()) for key in KEYS]
            self.next_frame = 0

        def job(self, *args, **kwargs):
            g['CONTEXT'].building_filters = tuple(flags)
            try:
                return super().job(*args, **kwargs)
            finally:
                del g['CONTEXT'].building_filters

        def building_filter_controls(self, parent):
            if getattr(parent, '_building_filters_layout', False):
                return
            parent._building_filters_layout = True
            for child in parent.winfo_children():
                child.destroy()
            definitions = [('Terreno', 'map_terrain'), ('Construções', 'central_buildings'), ('Deslocamentos', 'troops_map'), ('Pesquisas e eras', 'research_icons'), ('Gaia', 'gaia_show'), ('Ocultar militares', 'hide_military_buildings'), ('Ocultar econômicas', 'hide_economic_buildings'), ('Ocultar casas', 'hide_houses')]
            controls = []
            for label, key in definitions:
                if not hasattr(self, key):
                    continue
                control = ttk.Checkbutton(parent, text='  ' + label, variable=getattr(self, key), style='Switch.TCheckbutton', command=self.refresh_central)
                controls.append((key, control))
            positions = {'map_terrain': (0, 0), 'troops_map': (1, 0), 'central_buildings': (0, 1), 'research_icons': (1, 1), 'gaia_show': (2, 1), 'hide_military_buildings': (0, 2), 'hide_economic_buildings': (1, 2), 'hide_houses': (2, 2)}
            previous = [None]

            def layout(event=None):
                width = event.width if event is not None else parent.winfo_width()
                required = max((control.winfo_reqwidth() for _, control in controls), default=180) + 12
                columns = 3 if width >= required * 3 else 2 if width >= required * 2 else 1
                if columns == previous[0]:
                    return
                previous[0] = columns
                for index in range(3):
                    parent.columnconfigure(index, weight=1 if index < columns else 0, minsize=0, uniform='building_layers' if index < columns else '')
                for index, (key, control) in enumerate(controls):
                    control.grid_forget()
                    row, column = positions[key] if columns == 3 else divmod(index, columns)
                    control.grid(row=row, column=column, sticky='w', padx=(0, 8), pady=3)
            parent.bind('<Configure>', layout, add='+')
            parent.after_idle(layout)
    g['Window'] = Window
