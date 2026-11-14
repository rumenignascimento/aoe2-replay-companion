import ast
from datetime import datetime
from pathlib import Path
import shutil


def adaptar_painel(codigo):
    tree = ast.parse(codigo)
    found = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'prepare_units':
            node.body = ast.parse('from unidades_034 import preparar\npreparar(session, globals())').body
            found = True
    if not found:
        raise RuntimeError('Função prepare_units não reconhecida. Nenhum arquivo alterado.')
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def adaptar_gerador(codigo):
    tree = ast.parse(codigo)
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            names = [v.value for v in node.elts if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            if 'painel_jogadores.py' in names and 'central_replay.py' in names:
                found = True
                for name in ('unidades_034.py', 'unidades_assets_034.py'):
                    if name not in names:
                        node.elts.append(ast.Constant(name))
    if not found:
        raise RuntimeError('Lista de arquivos do instalador não reconhecida.')
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def main():
    root = Path(__file__).resolve().parent
    for name in ('painel_jogadores.py', 'gerar_instalador.py', 'unidades_034.py', 'unidades_assets_034.py'):
        if not (root / name).is_file():
            raise RuntimeError('Arquivo ausente: ' + name + '. Extraia todos os arquivos na pasta do projeto.')
    for name in ('unidades_034.py', 'unidades_assets_034.py'):
        ast.parse((root / name).read_text(encoding='utf-8-sig'), filename=name)
    changes = {
        'painel_jogadores.py': adaptar_painel((root / 'painel_jogadores.py').read_text(encoding='utf-8-sig')),
        'gerar_instalador.py': adaptar_gerador((root / 'gerar_instalador.py').read_text(encoding='utf-8-sig')),
    }
    for name, text in changes.items():
        ast.parse(text, filename=name)
    backup = root / 'backups_atualizacoes' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    for name in changes:
        shutil.copy2(root / name, backup / name)
    for name, text in changes.items():
        (root / name).write_text(text, encoding='utf-8')
    print('Correspondência de unidades atualizada. Backup:', backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.3.4, ou superior à última gerada.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERRO:', error)
        raise SystemExit(1)
