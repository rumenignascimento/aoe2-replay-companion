import ast
import shutil
from pathlib import Path
from datetime import datetime

MODULO = r'''
import sys
import tkinter as tk
from tkinter import ttk


def abrir(window, g):
    previous = getattr(window, '_shortcut_dialog', None)
    if previous is not None and previous.winfo_exists():
        previous.lift()
        previous.focus_set()
        return

    dialog = tk.Toplevel(window.root)
    window._shortcut_dialog = dialog
    dialog.title('Atalhos · pressione a combinação desejada')
    dialog.geometry('800x680')
    dialog.transient(window.root)

    message = tk.StringVar(
        master=dialog,
        value='Clique no campo ou em Capturar e pressione o atalho. Esc cancela.'
    )
    ttk.Label(
        dialog, textvariable=message,
        wraplength=740, padding=12
    ).pack(fill='x')

    footer = ttk.Frame(dialog, padding=10)
    footer.pack(side='bottom', fill='x')

    canvas = tk.Canvas(
        dialog, highlightthickness=0,
        bg=window.root.cget('bg')
    )
    scroll = ttk.Scrollbar(dialog, command=canvas.yview)
    scroll.pack(side='right', fill='y')
    canvas.configure(yscrollcommand=scroll.set)
    canvas.pack(fill='both', expand=True)

    body = ttk.Frame(canvas, padding=10)
    item = canvas.create_window(0, 0, window=body, anchor='nw')
    body.columnconfigure(1, weight=1)

    body.bind(
        '<Configure>',
        lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
    )
    canvas.bind(
        '<Configure>',
        lambda e: canvas.itemconfigure(item, width=e.width)
    )

    state = {'key': None, 'job': None, 'blocked': set()}
    entries = {}

    modifiers = (
        (0x11, 'Ctrl'),
        (0x12, 'Alt'),
        (0x10, 'Shift'),
        (0x5b, 'Win'),
    )

    keys = {
        ord(c): c for c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    }
    keys.update({
        0x70 + i - 1: 'F' + str(i)
        for i in range(1, 25)
    })

    names = {
        'LEFT': 'Left',
        'RIGHT': 'Right',
        'UP': 'Up',
        'DOWN': 'Down',
        'SPACE': 'Space',
        'HOME': 'Home',
        'END': 'End',
        'PGUP': 'PgUp',
        'PGDN': 'PgDn',
        'INSERT': 'Insert',
        'DELETE': 'Delete',
    }

    keys.update({
        vk: names[name]
        for name, vk in g['KEY_NAMES'].items()
        if name in names
    })

    native = window.native.u if sys.platform == 'win32' else None

    def down(vk):
        return bool(native.GetAsyncKeyState(vk) & 0x8000)

    def stop(text=None):
        if state['job'] is not None:
            dialog.after_cancel(state['job'])
            state['job'] = None

        state['key'] = None
        window._shortcut_recording = False

        if text:
            message.set(text)

    def accept(chord):
        key = state['key']
        if key is None:
            return

        spec = window.key_spec()
        spec[key] = chord

        try:
            g['validate_keys'](spec)
        except ValueError as error:
            message.set(
                str(error)
                + ' Escolha outra combinação ou pressione Esc.'
            )
            return

        getattr(window, 'key_' + key).set(chord)

        stop(
            'Capturado: ' + chord
            + '. Use Aplicar atalhos ou Salvar configurações.'
        )

    def poll():
        state['job'] = None

        if state['key'] is None or not dialog.winfo_exists():
            return

        if down(0x1b):
            stop('Captura cancelada. O atalho anterior foi mantido.')
            return

        state['blocked'] = {
            vk for vk in state['blocked'] if down(vk)
        }

        pressed = [
            vk for vk in keys
            if down(vk) and vk not in state['blocked']
        ]

        if pressed:
            state['blocked'].update(pressed)

            mods = [
                name for vk, name in modifiers if down(vk)
            ]

            if down(0x5c) and 'Win' not in mods:
                mods.append('Win')

            if mods:
                accept('+'.join(mods + [keys[pressed[0]]]))
            else:
                message.set(
                    'Inclua Ctrl, Alt, Shift ou Win '
                    'junto da tecla desejada.'
                )

        if state['key'] is not None:
            state['job'] = dialog.after(10, poll)

    def start(key):
        stop()
        state['key'] = key
        window._shortcut_recording = True
        entries[key].focus_set()

        message.set(
            'Pressione a combinação para este campo. '
            'Esc cancela; Limpar desativa o atalho.'
        )

        if native is not None:
            state['blocked'] = {
                vk for vk in keys if down(vk)
            }
            state['job'] = dialog.after(10, poll)

        return 'break'

    def event_key(event):
        if state['key'] is None:
            return

        if event.keysym == 'Escape':
            stop('Captura cancelada. O atalho anterior foi mantido.')

        elif native is None:
            aliases = {
                'Prior': 'PgUp',
                'Next': 'PgDn',
                'space': 'Space',
            }
            name = aliases.get(event.keysym, event.keysym)

            if len(name) == 1:
                name = name.upper()

            if name in keys.values():
                mods = [
                    label
                    for mask, label in (
                        (4, 'Ctrl'),
                        (8, 'Alt'),
                        (1, 'Shift'),
                    )
                    if event.state & mask
                ]

                if mods:
                    accept('+'.join(mods + [name]))

        return 'break'

    def clear(key):
        stop()
        getattr(window, 'key_' + key).set('')
        message.set(
            'Atalho limpo. Aplique ou salve para desativá-lo.'
        )

    def apply(save=False):
        stop()

        try:
            g['validate_keys'](window.key_spec())
        except ValueError as error:
            message.set(str(error))
            return

        if save:
            window.save_settings()
        else:
            window.apply_keys()

        message.set(
            'Solicitação enviada. Confira a confirmação '
            'ou eventual conflito no status do aplicativo.'
        )

    def close():
        stop()
        dialog.destroy()

    for row, (key, label, target) in enumerate(g['ACTIONS']):
        ttk.Label(body, text=label).grid(
            row=row, column=0,
            sticky='w', padx=6, pady=6
        )

        entry = ttk.Entry(
            body,
            textvariable=getattr(window, 'key_' + key),
            state='readonly',
            width=25,
        )
        entry.grid(
            row=row, column=1,
            sticky='ew', padx=6, pady=6
        )
        entries[key] = entry

        entry.bind(
            '<Button-1>',
            lambda e, k=key: start(k)
        )
        entry.bind(
            '<Return>',
            lambda e, k=key: start(k)
        )

        ttk.Button(
            body, text='Capturar',
            command=lambda k=key: start(k)
        ).grid(row=row, column=2, padx=4, pady=6)

        ttk.Button(
            body, text='Limpar',
            command=lambda k=key: clear(k)
        ).grid(row=row, column=3, padx=4, pady=6)

    ttk.Button(
        footer, text='Aplicar atalhos',
        command=apply
    ).pack(side='left')

    ttk.Button(
        footer, text='Salvar configurações',
        command=lambda: apply(True)
    ).pack(side='left', padx=8)

    ttk.Button(
        footer, text='Fechar',
        command=close
    ).pack(side='right')

    dialog.bind('<KeyPress>', event_key)

    def check_focus():
        if (
            dialog.winfo_exists()
            and state['key'] is not None
            and dialog.focus_displayof() is None
        ):
            stop('Captura cancelada ao sair do aplicativo.')

    dialog.bind(
        '<FocusOut>',
        lambda e: dialog.after_idle(check_focus)
    )
    dialog.bind(
        '<Destroy>',
        lambda e: stop() if e.widget is dialog else None
    )
    dialog.protocol('WM_DELETE_WINDOW', close)
'''


def main():
    root = Path(__file__).resolve().parent
    changes = {'captura_atalhos.py': MODULO}

    source = root / 'painel_horizontal.py'
    if not source.is_file():
        raise RuntimeError(
            'Salve na pasta completa do projeto, '
            'com painel_horizontal.py.'
        )

    tree = ast.parse(
        source.read_text(encoding='utf-8-sig')
    )
    found = False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'keys_dialog':
            node.body = ast.parse(
                'from captura_atalhos import abrir\n'
                'abrir(self, g)'
            ).body
            found = True

    if not found:
        raise RuntimeError('Janela de atalhos não reconhecida.')

    ast.fix_missing_locations(tree)
    changes[source.name] = ast.unparse(tree) + '\n'

    source = root / 'controles_camadas.py'
    if not source.is_file():
        raise RuntimeError('Módulo controles_camadas.py ausente.')

    tree = ast.parse(
        source.read_text(encoding='utf-8-sig')
    )
    found = False

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'choose':
            if '_shortcut_recording' not in ast.unparse(node):
                node.body[:0] = ast.parse(
                    "if getattr(self, '_shortcut_recording', False): return"
                ).body
            found = True

    if not found:
        raise RuntimeError('Controle de atalhos não reconhecido.')

    ast.fix_missing_locations(tree)
    changes[source.name] = ast.unparse(tree) + '\n'

    source = root / 'gerar_instalador.py'
    tree = ast.parse(
        source.read_text(encoding='utf-8-sig')
    )
    found = False

    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue

        names = [
            value.value
            for value in node.elts
            if isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        ]

        if (
            'painel_jogadores.py' in names
            and 'central_replay.py' in names
        ):
            found = True
            if 'captura_atalhos.py' not in names:
                node.elts.append(
                    ast.Constant('captura_atalhos.py')
                )

    if not found:
        raise RuntimeError('Gerador não reconhecido.')

    ast.fix_missing_locations(tree)
    changes[source.name] = ast.unparse(tree) + '\n'

    for name, text in changes.items():
        ast.parse(text, filename=name)

    backup = (
        root / 'backups_atualizacoes'
        / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    )
    backup.mkdir(parents=True)

    for name in changes:
        if (root / name).exists():
            shutil.copy2(root / name, backup / name)

    for name, text in changes.items():
        (root / name).write_text(text, encoding='utf-8')

    print('Captura de atalhos instalada.')
    print('Backup:', backup)
    print('Execute: py -3.12 gerar_atualizacao.py')
    print('Versão sugerida: 0.3.2 ou superior à última gerada.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERRO:', error)
        raise SystemExit(1)