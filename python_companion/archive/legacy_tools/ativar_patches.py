"""Adapta o gerador atual sem substituir módulos do Companion."""
import ast,shutil
from pathlib import Path
from datetime import datetime

def adaptar(source):
    tree=ast.parse(source)
    main=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    if any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='somente_executavel_patch' for t in n.targets) for n in main.body):return source
    main.body.insert(0,ast.parse("somente_executavel_patch = '--somente-executavel' in sys.argv").body[0])
    changed=0
    for n in ast.walk(main):
        if isinstance(n,ast.If) and ast.unparse(n.test)=='compilador is None':
            n.test=ast.parse('compilador is None and not somente_executavel_patch',mode='eval').body;changed+=1
    index=next((i for i,n in enumerate(main.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value)=='executar(*comando)'),None)
    if changed!=1 or index is None:raise RuntimeError('Gerador não reconhecido; nenhum arquivo foi alterado.')
    insert=ast.parse("""if somente_executavel_patch:
    import json
    resultado = {'dist': str(trabalho / 'dist' / 'AoE2Overlay'), 'python_build': str(python)}
    (projeto / 'ultimo_build_patch.json').write_text(json.dumps(resultado), encoding='utf-8')
    print('Build para patch concluído:', resultado['dist'])
    return
""").body
    main.body[index+1:index+1]=insert;ast.fix_missing_locations(tree)
    result=ast.unparse(tree)+'\n';compile(result,'gerar_instalador.py','exec');return result

def main():
    root=Path(__file__).resolve().parent;path=root/'gerar_instalador.py'
    original=path.read_text(encoding='utf-8-sig');result=adaptar(original)
    if result==original:print('Suporte a patches já está ativo.');return
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    shutil.copy2(path,backup/path.name)
    temp=path.with_suffix('.py.tmp');temp.write_text(result,encoding='utf-8');temp.replace(path)
    print('Suporte a builds sem Inno Setup ativado. Backup:',backup)
    print('Para gerar uma atualização: py -3.12 gerar_patch.py')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
