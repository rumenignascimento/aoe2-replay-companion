import ast
from datetime import datetime
from pathlib import Path
import shutil


def adaptar_horizontal(codigo):
    tree=ast.parse(codigo);found=False
    for cls in ast.walk(tree):
        if not isinstance(cls,ast.ClassDef) or cls.name!='Window':
            continue
        update=next((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='update_horizontal_panel'),None)
        if update is None:
            continue
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        if '_click_tabs_active' not in ast.unparse(init):
            init.body[:0]=ast.parse('self._click_tabs_active=True\nself._click_tab_manager=None\nself._click_tabs_failed=False').body
        if 'sync_clickable_tabs' not in ast.unparse(update):
            update.body=[ast.Try(body=update.body,handlers=[],orelse=[],finalbody=ast.parse('self.sync_clickable_tabs()').body)]
        if not any(isinstance(n,ast.FunctionDef) and n.name=='sync_clickable_tabs' for n in cls.body):
            cls.body.extend(ast.parse('def sync_clickable_tabs(self):\n    from abas_clicaveis_040 import sync\n    sync(self)').body)
        found=True
    if not found:raise RuntimeError('Painel horizontal não reconhecido.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def adaptar_tabela(codigo):
    tree=ast.parse(codigo);found=False
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name=='paint':
            if '_click_tabs_active' in ast.unparse(node):
                found=True;continue
            for item in ast.walk(node):
                if isinstance(item,ast.For) and ast.unparse(item.iter)=='enumerate(tabs)':
                    index=next((i for i,n in enumerate(item.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='x' for t in n.targets)),None)
                    if index is None:raise RuntimeError('Geometria das abas não reconhecida.')
                    item.body[index+1:index+1]=ast.parse("if getattr(window,'_click_tabs_active',False):\n    canvas.create_rectangle(x,6,x+tab_width+1,30,fill='#ff00ff',outline='',width=0)\n    continue").body
                    found=True
    if not found:raise RuntimeError('Renderização da tabela não reconhecida. Aplique a atualização da tabela antes.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def adaptar_gerador(codigo):
    tree=ast.parse(codigo);found=False
    for node in ast.walk(tree):
        if isinstance(node,ast.List):
            names=[v.value for v in node.elts if isinstance(v,ast.Constant) and isinstance(v.value,str)]
            if 'painel_jogadores.py' in names and 'central_replay.py' in names:
                if 'abas_clicaveis_040.py' not in names:node.elts.append(ast.Constant('abas_clicaveis_040.py'))
                found=True
    if not found:raise RuntimeError('Gerador não reconhecido.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def main():
    root=Path(__file__).resolve().parent
    required=('abas_clicaveis_040.py','painel_horizontal.py','painel_tabela_036.py','gerar_instalador.py')
    for name in required:
        if not (root/name).is_file():raise RuntimeError('Arquivo ausente: '+name+'. Extraia o pacote na pasta completa do projeto.')
    ast.parse((root/'abas_clicaveis_040.py').read_text(encoding='utf-8-sig'))
    changes={name:fn((root/name).read_text(encoding='utf-8-sig')) for name,fn in (
        ('painel_horizontal.py',adaptar_horizontal),('painel_tabela_036.py',adaptar_tabela),('gerar_instalador.py',adaptar_gerador))}
    for name,text in changes.items():ast.parse(text,filename=name)
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    for name in changes:shutil.copy2(root/name,backup/name)
    for name,text in changes.items():(root/name).write_text(text,encoding='utf-8')
    print('Abas clicáveis adicionadas. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.4.0, ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
