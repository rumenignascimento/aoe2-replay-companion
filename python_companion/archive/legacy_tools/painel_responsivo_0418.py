import ast
import shutil
from pathlib import Path
from datetime import datetime

CONTROLS = "def _controles_icones_0418(window, parent):\n    box = ttk.LabelFrame(parent, text='Ícones do painel horizontal', padding=6)\n    box.pack(fill='x', pady=6)\n    window.field(box, 'Tamanho desejado (px)', window.panel_icon_size, bounds=(12, 96))\n    value = tk.DoubleVar(master=window.root, value=window.panel_icon_size.get())\n    guard = [False]\n    def from_field(*args):\n        if guard[0]:\n            return\n        try:\n            size = int(window.panel_icon_size.get())\n            if 12 <= size <= 96:\n                guard[0] = True\n                value.set(size)\n        except (ValueError, tk.TclError):\n            pass\n        finally:\n            guard[0] = False\n    def from_slider(raw):\n        if guard[0]:\n            return\n        guard[0] = True\n        try:\n            window.panel_icon_size.set(max(12, min(96, round(float(raw)))))\n        finally:\n            guard[0] = False\n    ttk.Scale(box, from_=12, to=96, variable=value, command=from_slider).pack(fill='x', pady=3)\n    trace = window.panel_icon_size.trace_add('write', from_field)\n    ttk.Label(box, textvariable=window.panel_icon_effective, wraplength=210).pack(anchor='w', pady=3)\n    ttk.Label(box, text='Ícones e textos se ajustam ao espaço disponível. Pesquisas usam ícones menores.', wraplength=210).pack(anchor='w')\n    def cleanup(event):\n        if event.widget is box:\n            try:\n                window.panel_icon_size.trace_remove('write', trace)\n            except tk.TclError:\n                pass\n    box.bind('<Destroy>', cleanup, add='+')\n    return box\n"


def function(tree, name):
    found=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name]
    if len(found)!=1:raise RuntimeError('Função não reconhecida: '+name)
    return found[0]


def adaptar_horizontal(source):
    tree=ast.parse(source)
    activate=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ativar'),None)
    if activate is None:raise RuntimeError('Integração horizontal não reconhecida.')
    validate=function(activate,'validate')
    if not any('panel_icon_size' in ast.unparse(n) for n in validate.body):
        migrate=ast.parse("if isinstance(values, dict) and 'panel_icon_size' not in values:\n    values = dict(values)\n    old_size = values.get('bar_size', 32)\n    values['panel_icon_size'] = max(12, min(96, old_size)) if isinstance(old_size, int) and not isinstance(old_size, bool) else 32").body
        validate.body[:0]=migrate
        last=next(n for n in reversed(validate.body) if isinstance(n,ast.Return))
        check=ast.parse("icon_size = result['panel_icon_size']\nif isinstance(icon_size, bool) or not isinstance(icon_size, int) or not 12 <= icon_size <= 96:\n    raise ValueError('Ícones do painel: use um inteiro entre 12 e 96.')").body
        i=validate.body.index(last);validate.body[i:i]=check
    for node in activate.body:
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and ast.unparse(node.value.func)=="g['p'].CONFIG_DEFAULTS.update":
            if not any(k.arg=='panel_icon_size' for k in node.value.keywords):node.value.keywords.append(ast.keyword(arg='panel_icon_size',value=ast.Constant(value=32)))
    window=next(n for n in activate.body if isinstance(n,ast.ClassDef) and n.name=='Window')
    init=function(window,'__init__')
    if not any('self.panel_icon_size =' in ast.unparse(n) for n in init.body):
        init.body[:0]=ast.parse("self.panel_icon_size = tk.IntVar(master=root, value=32)\nself.panel_icon_effective = tk.StringVar(master=root, value='Aplicado: automático')").body
        init.body.append(ast.parse("self.panel_icon_size.trace_add('write', self.panel_changed)").body[0])
    update=function(window,'update_horizontal_panel')
    changed=0
    for node in ast.walk(update):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='size' for t in node.targets) and 'number(self.bar_size' in ast.unparse(node.value):
            node.value=ast.parse("min(number(self.panel_icon_size, 32, 12, 96), max(12, int((width - 16) / 2.5)))",mode='eval').body;changed+=1
        elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='size' for t in node.targets) and 'number(self.panel_icon_size' in ast.unparse(node.value):changed+=1
    if changed!=1:raise RuntimeError('Ajuste de tamanho horizontal não reconhecido.')
    for node in ast.walk(update):
        if isinstance(node,ast.Try):
            if any(isinstance(n,ast.Expr) and 'self.panel_icon_effective.set' in ast.unparse(n) for n in node.body):continue
            i=next((i for i,n in enumerate(node.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='index' for t in n.targets)),None)
            if i is not None:
                node.body.insert(i+1,ast.parse("self.panel_icon_effective.set('Aplicado: ' + str(pages[index]['icon_size']) + ' px · ajustado ao espaço')").body[0])
                break
    position=function(window,'setup_table_position_controls')
    if not any(isinstance(n,ast.Expr) and '_controles_icones_0418(' in ast.unparse(n) for n in position.body):
        i=next((i for i,n in enumerate(position.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='self.switch'),None)
        if i is None:raise RuntimeError('Controles de posição do painel não reconhecidos.')
        position.body.insert(i+1,ast.parse('_controles_icones_0418(self, box)').body[0])
    tree.body[:]=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='_controles_icones_0418')]
    tree.body.insert(tree.body.index(activate),ast.parse(CONTROLS).body[0])
    ast.fix_missing_locations(tree);result=ast.unparse(tree)+'\n';compile(result,'painel_horizontal.py','exec');return result


def adaptar_tabela(source):
    tree=ast.parse(source)
    layout=function(tree,'panel_layout')
    for node in ast.walk(layout):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='size' for t in node.targets) and 'min(col_widths[0], col_widths[1])' in ast.unparse(node.value):
            node.value=ast.parse("min(size, max(10, min(col_widths[0], col_widths[1]) - 8), max(10, int((col_widths[2] - 15) / 1.5)))",mode='eval').body
    paint=function(tree,'paint')
    if not any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='font_px' for t in n.targets) for n in paint.body):
        i=next(i for i,n in enumerate(paint.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='normal' for t in n.targets))
        paint.body.insert(i,ast.parse('font_px = max(9, min(16, round(size * 0.36)))').body[0])
    for node in ast.walk(paint):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('normal','bold','tab_font') for t in node.targets) and isinstance(node.value,ast.Call):
            for keyword in node.value.keywords:
                if keyword.arg=='size':keyword.value=ast.parse('-font_px' if any(isinstance(t,ast.Name) and t.id!='tab_font' for t in node.targets) else '-max(10, min(16, font_px))',mode='eval').body
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='count_size' for t in node.targets):
            node.value=ast.parse("max(6, min(16, round(size * 0.36), int((token['width'] - 4) / (max(1, len(digits)) * 0.7))))",mode='eval').body
        if isinstance(node,ast.Tuple) and len(node.elts)==3 and isinstance(node.elts[0],ast.Name) and node.elts[0].id=='body':
            if isinstance(node.elts[1],ast.Name) and node.elts[1].id=='count_size':node.elts[1]=ast.UnaryOp(op=ast.USub(),operand=ast.Name(id='count_size',ctx=ast.Load()))
            elif isinstance(node.elts[1],ast.Constant) and node.elts[1].value==8:node.elts[1]=ast.parse('-max(7, min(12, round(small * 0.6)))',mode='eval').body
    ast.fix_missing_locations(tree);result=ast.unparse(tree)+'\n';compile(result,'painel_tabela_036.py','exec');return result


def main():
    root=Path(__file__).resolve().parent
    original={};results={}
    for name,adapt in [('painel_horizontal.py',adaptar_horizontal),('painel_tabela_036.py',adaptar_tabela)]:
        path=root/name
        if not path.is_file():raise RuntimeError('Arquivo ausente: '+name+'. Extraia o atualizador na pasta GeradorMapaAoE2.')
        original[name]=path.read_bytes();results[name]=adapt(original[name].decode('utf-8-sig'))
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    for name in original:shutil.copy2(root/name,backup/name)
    try:
        for name,code in results.items():(root/name).write_text(code,encoding='utf-8')
    except Exception:
        for name in original:shutil.copy2(backup/name,root/name)
        raise
    print('Painel responsivo e tamanho independente de ícones aplicados. Backup:',backup)
    print('Controle em Overlay > Posição > Painel horizontal: Ícones do painel horizontal.')
    print('Execute py -3.12 gerar_atualizacao.py. Use versão 0.4.18 ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('ERRO:',error);raise SystemExit(1)
