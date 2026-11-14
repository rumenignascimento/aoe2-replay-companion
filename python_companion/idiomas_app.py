"""Localização de apresentação. Valores internos e arquivos do jogo não mudam."""
import os
import ast
import json
import re
import tkinter as tk
from tkinter import ttk

from catalogo_idiomas import CATALOGO, AJUDA, LANGUAGES, EXTRAS_PT


def idioma():
    value = os.environ.get('AOE2_LANGUAGE', '')
    if not value:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\AoE2Overlay') as key:
                value = winreg.QueryValueEx(key, 'Language')[0]
        except (ImportError, OSError):
            value = 'brazilianportuguese'
    value = {'english': 'en', 'spanish': 'es', 'brazilianportuguese': 'pt'}.get(value, value)
    return value if value in dict(LANGUAGES) else 'pt'


LANG = idioma()


def tr(value):
    if LANG == 'pt' or not isinstance(value, str) or not value:
        return value
    table = CATALOGO[LANG]
    if value in table:
        return table[value]
    if value == 'Aguardando dados do computador…':
        return tr('Conectando ao computador…')
    if value.startswith('Atualização contínua.'):
        suffix = value[len('Atualização contínua.'):].strip()
        legacy = next((source for source in table if source.startswith('Atualização-alvo:') and suffix and source.endswith(suffix)), None)
        if legacy:
            translated = table[legacy]
            return re.split(r'[.!?。।]\s*', translated, maxsplit=1)[-1]
    stripped = value.strip()
    if stripped != value:
        return value[:len(value)-len(value.lstrip())] + tr(stripped) + value[len(value.rstrip()):]
    if '\n' in value:
        return '\n'.join(tr(line) for line in value.split('\n'))
    patterns = [
        (r'Jogador (\d+)', 'Jogador {0}'),
        (r'J(\d+)', 'J{0}'),
        (r'(\d+) pedidos · construções', '{0} pedidos · construções'),
        (r'(\d+) pedidos · produção', '{0} pedidos · produção'),
        (r'(\d+) pedidos · pesquisas', '{0} pedidos · pesquisas'),
        (r'PEDIDOS · página (\d+)/(\d+)', 'PEDIDOS · página {0}/{1}'),
        (r'(\d+) de (\d+) tópicos', '{0} de {1} tópicos'),
        (r'Capturado: (.+)\. Use Aplicar atalhos ou Salvar configurações\.',
         'Capturado: {0}. Use Aplicar atalhos ou Salvar configurações.'),
    ]
    for pattern, template in patterns:
        match = re.fullmatch(pattern, value)
        if match:
            return table.get(template, template).format(*match.groups())
    if value.startswith('Camadas: '):
        return tr('Camadas e informações') + ': ' + tr(value[8:])
    if value.startswith('● '):
        return '● ' + tr(value[2:])
    # Fragmentos dinâmicos conhecidos; não traduz caminhos ou nomes de arquivos.
    if not re.search(r'[A-Za-z]:[\\/]|https?://|\.(aoe2record|json|py|exe)\b', value):
        fragments = ('Replay até', 'Atualizado há', 'aguardando novos registros', 'finalizado')
        for source in fragments:
            if source in value:
                value = value.replace(source, table.get(source, source))
    return value


def ajuda_localizada(topics):
    if LANG != 'pt':
        return AJUDA.get(LANG, topics)
    titles = {title for title, body in topics}
    return list(topics) + [item for item in EXTRAS_PT if item[0] not in titles]


def traduzir_html(html):
    if LANG == 'pt':
        return html
    html = html.replace('lang="pt-BR"', 'lang="' + LANG + '"')
    def literal(match):
        try:
            value = ast.literal_eval(match.group())
        except (ValueError, SyntaxError):
            return match.group()
        result = tr(value)
        return json.dumps(result, ensure_ascii=False) if result != value else match.group()
    def script(match):
        body = re.sub(r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", literal, match.group(2))
        return match.group(1) + body + match.group(3)
    pieces = re.split(r'(<script\b[^>]*>.*?</script>)', html, flags=re.S | re.I)
    for index, part in enumerate(pieces):
        if part.lower().startswith('<script'):
            pieces[index] = re.sub(r'(<script\b[^>]*>)(.*?)(</script>)', script, part, flags=re.S | re.I)
        else:
            part = re.sub(r'>([^<>]+)<', lambda m: '>' + tr(m.group(1)) + '<', part)
            part = re.sub(r'((?:alt|title|aria-label)=")(.*?)(")', lambda m: m.group(1) + tr(m.group(2)).replace('"', '&quot;') + m.group(3), part)
            pieces[index] = part
    return ''.join(pieces)


class Ponte:
    def __init__(self, proxy, path, original, values=None):
        self.proxy = proxy
        self.original = original
        self.values = values
        self.busy = False
        proxy.serial += 1
        self.display = 'aoe_i18n_' + str(proxy.serial)
        self.callbacks = []
        for variable, callback in ((original, self.forward), (self.display, self.backward)):
            name = proxy.root.register(callback)
            proxy.raw.call('trace', 'add', 'variable', variable, 'write', name)
            self.callbacks.append((variable, name))
        self.forward()

    def forward(self, *args):
        if self.busy:
            return
        self.busy = True
        try:
            try:
                value = self.proxy.raw.getvar(self.original)
            except tk.TclError:
                value = ''
            self.proxy.raw.setvar(self.display, tr(value))
        finally:
            self.busy = False

    def backward(self, *args):
        if self.busy or self.values is None:
            return
        value = self.proxy.raw.getvar(self.display)
        original = next((v for v in self.values if tr(v) == value), value)
        self.busy = True
        try:
            self.proxy.raw.setvar(self.original, original)
        finally:
            self.busy = False

    def close(self):
        for variable, name in self.callbacks:
            try:
                self.proxy.raw.call('trace', 'remove', 'variable', variable, 'write', name)
                self.proxy.root.deletecommand(name)
            except tk.TclError:
                pass
        try:
            self.proxy.raw.call('unset', '-nocomplain', self.display)
        except tk.TclError:
            pass


class TradutorTk:
    def __init__(self, root, raw):
        self.root = root
        self.raw = raw
        self.types = {}
        self.options = {}
        self.bridges = {}
        self.serial = 0

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def call(self, *args):
        if len(args) == 1 and isinstance(args[0], (tuple, list)):
            args = tuple(args[0])
        if not args:
            return self.raw.call(*args)
        a = list(args)
        command = str(a[0])
        if command == 'destroy':
            for target in a[1:]:
                for path in list(self.bridges):
                    if path == str(target) or path.startswith(str(target) + '.'):
                        self.bridges.pop(path).close()
            return self.raw.call(*a)
        if command == 'wm' and len(a) >= 4 and a[1] == 'title':
            a[3] = tr(a[3])
        if command in ('tk_messageBox', 'tk_getOpenFile', 'tk_getSaveFile', 'tk_chooseDirectory'):
            for index in range(1, len(a) - 1):
                if a[index] in ('-title', '-message', '-detail'):
                    a[index + 1] = tr(a[index + 1])
        path = None
        start = None
        if (command.startswith('ttk::') or command in ('label', 'button', 'checkbutton', 'radiobutton', 'labelframe', 'menubutton', 'menu', 'text', 'listbox', 'canvas', 'entry')) and len(a) > 1 and str(a[1]).startswith('.'):
            path = str(a[1]); self.types[path] = command
            start = 2
        elif command.startswith('.') and len(a) > 1:
            path = command
            kind = self.types.get(path, '')
            operation = str(a[1])
            if operation == 'cget' and len(a) == 3:
                stored = self.options.get((path, str(a[2])))
                if stored is not None:
                    return stored
            if kind == 'ttk::combobox' and operation == 'get':
                value = self.raw.call(*a)
                return next((v for v in self.options.get((path, '-values'), ()) if tr(v) == value), value)
            if kind == 'ttk::combobox' and operation == 'set' and len(a) == 3:
                a[2] = tr(a[2])
            if kind == 'listbox' and operation == 'insert':
                a[3:] = [tr(v) for v in a[3:]]
            if kind == 'text' and operation == 'insert':
                for index in range(3, len(a), 2):
                    a[index] = tr(a[index])
            if operation in ('configure', 'config'):
                start = 2
            elif operation in ('add', 'insert', 'entryconfigure', 'tab', 'create', 'itemconfigure'):
                start = next((i for i in range(2, len(a)) if isinstance(a[i], str) and a[i].startswith('-')), None)
        if path and start is not None:
            kind = self.types.get(path, '')
            options = {str(a[i]): a[i + 1] for i in range(start, len(a) - 1, 2)}
            if '-values' in options and kind == 'ttk::combobox':
                value = options['-values']
                values = tuple(value) if isinstance(value, (tuple, list)) else self.raw.splitlist(value)
                self.options[path, '-values'] = values
                if path in self.bridges:
                    self.bridges[path].values = values
            if '-textvariable' in options and options['-textvariable'] and kind in ('label', 'ttk::label', 'button', 'ttk::button', 'checkbutton', 'ttk::checkbutton', 'ttk::combobox'):
                original = str(options['-textvariable'])
                if path in self.bridges:
                    self.bridges.pop(path).close()
                self.options[path, '-textvariable'] = original
                values = self.options.get((path, '-values'), ()) if kind == 'ttk::combobox' else None
                self.bridges[path] = Ponte(self, path, original, values)
            for i in range(start, len(a) - 1, 2):
                option = str(a[i])
                if option in ('-text', '-label'):
                    # Somente opções do próprio widget são guardadas como cget.
                    if kind not in ('ttk::notebook', 'menu', 'canvas'):
                        self.options[path, option] = a[i + 1]
                    a[i + 1] = tr(a[i + 1])
                elif option == '-values' and kind == 'ttk::combobox':
                    a[i + 1] = tuple(tr(v) for v in self.options[path, '-values'])
                elif option == '-textvariable' and path in self.bridges:
                    a[i + 1] = self.bridges[path].display
        return self.raw.call(*a)


def instalar():
    if LANG == 'pt' or getattr(tk, '_aoe_i18n', False):
        return
    tk._aoe_i18n = True
    original = tk.Tk.__init__
    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        self.tk = TradutorTk(self, self.tk)
    tk.Tk.__init__ = init


def fonte_interface(fallback):
    if LANG in ('pt', 'en', 'es'):
        return fallback
    from tkinter import font
    choices = {
        'zh-CN': ('Microsoft YaHei UI', 'Microsoft YaHei'),
        'zh-TW': ('Microsoft JhengHei UI', 'Microsoft JhengHei'),
        'ja': ('Yu Gothic UI', 'Meiryo'),
        'ko': ('Malgun Gothic',),
        'th': ('Leelawadee UI', 'Tahoma'),
        'lo': ('Leelawadee UI',),
        'km': ('Leelawadee UI',),
        'my': ('Myanmar Text',),
    }.get(LANG, ('Nirmala UI', 'Segoe UI', 'Tahoma'))
    available = set(font.families())
    return next((name for name in choices if name in available), fallback)
