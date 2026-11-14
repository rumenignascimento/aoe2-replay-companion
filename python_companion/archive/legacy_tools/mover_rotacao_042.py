import ast
import shutil
from pathlib import Path
from datetime import datetime

CONTROLES = "def _orientacao_mapa_042(window):\n    import tkinter as tk\n    from tkinter import ttk\n    existing = getattr(window, '_orientation_toolbar_042', None)\n    if existing is not None and existing.winfo_exists():\n        return\n    canvas = window.preview_canvas\n    toolbar = ttk.Frame(canvas.master, style='Card.TFrame')\n    toolbar.pack(fill='x', before=canvas, padx=10, pady=(0,8))\n    window._orientation_toolbar_042 = toolbar\n    ttk.Label(toolbar, text='Rotação').pack(side='left', padx=(0,6))\n    combo = ttk.Combobox(toolbar, textvariable=window.map_turn,\n                         values=('0°','90°','180°','270°'),\n                         state='readonly', width=7)\n    combo.pack(side='left', padx=(0,8))\n    window._orientation_combo_042 = combo\n    def update():\n        if hasattr(window, 'map_options'):\n            window.map_options()\n        window.next_frame = 0\n        if hasattr(window, 'refresh_central'):\n            window.refresh_central()\n    def rotate(step):\n        try:\n            angle = int(str(window.map_turn.get()).replace('°','').strip())\n        except (ValueError,tk.TclError):\n            angle = 0\n        window.map_turn.set(str((angle+step)%360)+'°')\n        update()\n    combo.bind('<<ComboboxSelected>>', lambda event:update())\n    window._orientation_left_042 = ttk.Button(toolbar, text='-90°', width=5, command=lambda:rotate(-90))\n    window._orientation_left_042.pack(side='left', padx=(0,4))\n    window._orientation_right_042 = ttk.Button(toolbar, text='+90°', width=5, command=lambda:rotate(90))\n    window._orientation_right_042.pack(side='left', padx=(0,10))\n    window._orientation_mirror_042 = ttk.Checkbutton(toolbar, text='Espelhar mapa', variable=window.map_mirror, command=update)\n    window._orientation_mirror_042.pack(side='left')\n"


def adaptar(codigo):
    tree = ast.parse(codigo)
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name == 'build_central':
            if 'preview_canvas' not in ast.unparse(node):
                raise RuntimeError('Prévia do minimapa não reconhecida.')
            if '_orientacao_mapa_042' not in ast.unparse(node):
                node.body.extend(ast.parse('_orientacao_mapa_042(self)').body)
            found = True
        elif node.name == 'navigate':
            class Limpar(ast.NodeTransformer):
                def visit_Expr(self, statement):
                    call = statement.value
                    if isinstance(call, ast.Call) and ast.unparse(call.func) in ('self.field','self.switch') and len(call.args)>2:
                        if ast.unparse(call.args[2]) in ('self.map_turn','self.map_mirror'):
                            return None
                    return self.generic_visit(statement)
                def visit_If(self, statement):
                    self.generic_visit(statement)
                    if not statement.body:
                        statement.body = [ast.Pass()]
                    return statement
            Limpar().visit(node)
    if not found:
        raise RuntimeError('Função build_central não encontrada. Nenhum arquivo alterado.')
    tree.body[:] = [node for node in tree.body if not isinstance(node,ast.FunctionDef) or node.name!='_orientacao_mapa_042']
    tree.body.extend(ast.parse(CONTROLES).body)
    ast.fix_missing_locations(tree)
    resultado = ast.unparse(tree)+'\n'
    ast.parse(resultado)
    return resultado


def main():
    root = Path(__file__).resolve().parent
    target = root/'central_replay.py'
    if not target.is_file():
        raise RuntimeError('Salve este atualizador na pasta GeradorMapaAoE2, junto de central_replay.py.')
    codigo = adaptar(target.read_text(encoding='utf-8-sig'))
    backup = root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    shutil.copy2(target,backup/target.name)
    target.write_text(codigo,encoding='utf-8')
    print('Rotação e espelhamento movidos para cima da prévia do minimapa.')
    print('Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.4.2, ou superior à última gerada.')


if __name__=='__main__':
    try:
        main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
