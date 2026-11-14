import tkinter as tk
from tkinter import ttk
LAYERS = (('terrain', 'Terreno', 'map_terrain'), ('movements', 'Deslocamentos', 'troops_map'), ('buildings', 'Construções', 'central_buildings'), ('research', 'Pesquisas e eras', 'research_icons'), ('gaia', 'Gaia', 'gaia_show'), ('hide_military', 'Ocultar militares', 'hide_military_buildings'), ('hide_economic', 'Ocultar econômicas', 'hide_economic_buildings'), ('hide_houses', 'Ocultar casas', 'hide_houses'))

def ativar(g):
    if g.get('_controles_camadas_ativos'):
        return
    g['_controles_camadas_ativos'] = True
    additions = []
    for index, (key, label, variable) in enumerate(LAYERS):
        action = 'layer_' + key
        target = -30 - index
        chord = f'Ctrl+Alt+Shift+{index + 1}'
        g['ACTIONS'].append((action, 'Camadas: ' + label, target))
        g['DEFAULT_KEYS'][action] = chord
        g['p'].CONFIG_DEFAULTS['key_' + action] = chord
        additions.append((action, chord))
    old_validate = g['p']._validate_config

    def validate(values):
        if isinstance(values, dict):
            values = dict(values)
            used = set()
            for key in g['DEFAULT_KEYS']:
                if 'key_' + key in values:
                    chord = g['parse_key'](values['key_' + key])
                    if chord is not None:
                        used.add(chord)
            for key, default in additions:
                if 'key_' + key not in values:
                    chord = g['parse_key'](default)
                    values['key_' + key] = '' if chord in used else default
                    if chord not in used:
                        used.add(chord)
        return old_validate(values)
    g['p']._validate_config = validate
    Base = g['Window']

    class Window(Base):

        def __init__(self, root, native):
            self._position_slider_vars = {}
            self._position_slider_guards = set()
            super().__init__(root, native)

        def choose(self, target):
            if getattr(self, '_shortcut_recording', False):
                return
            index = -target - 30
            if 0 <= index < len(LAYERS):
                _, label, name = LAYERS[index]
                variable = getattr(self, name, None)
                if variable is None:
                    self.status.set('Camada indisponível nesta versão: ' + label)
                    return
                variable.set(not bool(variable.get()))
                self.next_frame = 0
                return
            return super().choose(target)

        def add_position_slider(self, parent, axis):
            variable = getattr(self, 'position_' + axis)
            limit = max(1, self.root.winfo_screenwidth() if axis == 'x' else self.root.winfo_screenheight())
            try:
                value = float(variable.get())
            except (ValueError, tk.TclError):
                value = 0
            slider_value = tk.DoubleVar(master=self.root, value=max(0, min(limit, value)))
            self._position_slider_vars[axis] = slider_value

            def from_slider(value):
                if axis in self._position_slider_guards:
                    return
                self._position_slider_guards.add(axis)
                try:
                    result = max(0, min(10000, round(float(value))))
                    variable.set(str(result))
                    slider_value.set(min(limit, result))
                finally:
                    self._position_slider_guards.discard(axis)

            def from_field(*args):
                if axis in self._position_slider_guards:
                    return
                try:
                    value = float(variable.get())
                except (ValueError, tk.TclError):
                    return
                self._position_slider_guards.add(axis)
                try:
                    slider_value.set(max(0, min(limit, value)))
                finally:
                    self._position_slider_guards.discard(axis)
            variable.trace_add('write', from_field)
            slider = ttk.Scale(parent, from_=0, to=limit, variable=slider_value, command=from_slider)
            slider.pack(fill='x', pady=(0, 10))
            setattr(self, 'position_slider_' + axis, slider)
    g['Window'] = Window
