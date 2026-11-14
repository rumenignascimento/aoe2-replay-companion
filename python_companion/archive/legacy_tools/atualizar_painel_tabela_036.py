import ast
from datetime import datetime
from pathlib import Path
import shutil


def adaptar_horizontal(codigo):
    tree=ast.parse(codigo);found=set()
    for node in ast.walk(tree):
        if not isinstance(node,ast.FunctionDef):
            continue
        if node.name=='panel_layout':
            node.args=ast.parse('def panel_layout(rows,width,size,max_height,players=()): pass').body[0].args
            node.body=ast.parse('from painel_tabela_036 import panel_layout as layout\nreturn layout(rows,width,size,max_height,players)').body
            found.add('layout')
        elif node.name=='paint_horizontal':
            node.body=ast.parse('from painel_tabela_036 import paint\npaint(self,page,width,size,index,total)').body
            found.add('paint')
        elif node.name=='update_horizontal_panel':
            for item in ast.walk(node):
                if isinstance(item,ast.Call) and isinstance(item.func,ast.Name) and item.func.id=='panel_layout':
                    if not any(k.arg=='players' for k in item.keywords):
                        item.keywords.append(ast.keyword(arg='players',value=ast.parse("self.bar_state.get('per_player', [])",mode='eval').body))
                    found.add('call')
                if isinstance(item,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='cache' for t in item.targets):
                    if isinstance(item.value,ast.Tuple) and 'player_name' not in ast.unparse(item.value):
                        item.value.elts.append(ast.parse("tuple((p['player'],p.get('player_name','')) for p in self.bar_state.get('per_player',[]))",mode='eval').body)
    if found!={'layout','paint','call'}:
        raise RuntimeError('Estrutura do painel horizontal não reconhecida: '+str(found))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def adaptar_jogadores(codigo):
    tree=ast.parse(codigo);found=False
    for node in tree.body:
        if isinstance(node,ast.FunctionDef) and node.name=='world_state':
            if 'nomes_jogadores' not in ast.unparse(node):
                node.body[:0]=ast.parse('from painel_tabela_036 import nomes_jogadores').body
                for item in ast.walk(node):
                    if isinstance(item,ast.Return) and item.value is not None:
                        item.value=ast.Call(func=ast.Name(id='nomes_jogadores',ctx=ast.Load()),args=[item.value,ast.Name(id='session',ctx=ast.Load())],keywords=[])
            found=True
    if not found:
        raise RuntimeError('Fonte dos jogadores não reconhecida.')
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def adaptar_gerador(codigo):
    tree=ast.parse(codigo);found=False
    for node in ast.walk(tree):
        if isinstance(node,ast.List):
            names=[n.value for n in node.elts if isinstance(n,ast.Constant) and isinstance(n.value,str)]
            if 'painel_jogadores.py' in names and 'central_replay.py' in names:
                if 'painel_tabela_036.py' not in names:
                    node.elts.append(ast.Constant('painel_tabela_036.py'))
                found=True
    if not found:
        raise RuntimeError('Lista de arquivos do instalador não reconhecida.')
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def main():
    root=Path(__file__).resolve().parent
    for name in ('painel_horizontal.py','painel_jogadores.py','gerar_instalador.py','painel_tabela_036.py'):
        if not (root/name).is_file():
            raise RuntimeError('Arquivo ausente: '+name+'. Extraia o pacote completo na pasta do projeto.')
    ast.parse((root/'painel_tabela_036.py').read_text(encoding='utf-8-sig'))
    changes={name:fn((root/name).read_text(encoding='utf-8-sig')) for name,fn in (
        ('painel_horizontal.py',adaptar_horizontal),('painel_jogadores.py',adaptar_jogadores),('gerar_instalador.py',adaptar_gerador))}
    for name,text in changes.items():
        ast.parse(text,filename=name)
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    for name in changes:
        shutil.copy2(root/name,backup/name)
    for name,text in changes.items():
        (root/name).write_text(text,encoding='utf-8')
    print('Painel em tabela instalado. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.3.6, ou superior à última gerada.')


if __name__=='__main__':
    try:
        main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
