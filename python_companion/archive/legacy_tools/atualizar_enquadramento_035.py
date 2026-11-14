import ast
from datetime import datetime
from pathlib import Path
import shutil


def main():
    root = Path(__file__).resolve().parent
    names = ('enquadramento_035.py', 'painel_jogadores.py', 'central_replay.py', 'mapa_overlay.py', 'gerar_instalador.py')
    for name in names:
        if not (root/name).is_file():
            raise RuntimeError('Arquivo ausente: ' + name + '. Extraia o pacote na pasta completa do projeto.')
    ast.parse((root/'enquadramento_035.py').read_text(encoding='utf-8-sig'))
    changes = {}
    tree = ast.parse((root/'painel_jogadores.py').read_text(encoding='utf-8-sig'))
    if '_ativar_enquadramento_035(globals())' not in ast.unparse(tree):
        index = next((i for i,n in enumerate(tree.body) if isinstance(n, ast.ImportFrom) and n.module == 'painel_movel'), None)
        if index is None:
            index = next((i for i,n in enumerate(tree.body) if isinstance(n, ast.If) and '__name__' in ast.unparse(n.test)), None)
        if index is None:
            raise RuntimeError('Inicialização do painel não reconhecida.')
        tree.body[index:index] = ast.parse('from enquadramento_035 import ativar as _ativar_enquadramento_035\n_ativar_enquadramento_035(globals())').body
    ast.fix_missing_locations(tree);changes['painel_jogadores.py'] = ast.unparse(tree)+'\n'
    tree = ast.parse((root/'central_replay.py').read_text(encoding='utf-8-sig'))
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'build_central':
            if 'setup_minimap_fit_controls' not in ast.unparse(node):
                index = next((i for i,n in enumerate(node.body) if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and ast.unparse(n.value.func) == 'self.field' and len(n.value.args)>1 and isinstance(n.value.args[1], ast.Constant) and n.value.args[1].value == 'Margem Y (px)'), None)
                if index is None:
                    raise RuntimeError('Controles de posição não reconhecidos.')
                node.body[index+1:index+1] = ast.parse("if hasattr(self, 'setup_minimap_fit_controls'): self.setup_minimap_fit_controls(position)").body
            found = True
    if not found:
        raise RuntimeError('Central não reconhecida.')
    ast.fix_missing_locations(tree);changes['central_replay.py'] = ast.unparse(tree)+'\n'
    tree = ast.parse((root/'mapa_overlay.py').read_text(encoding='utf-8-sig'))
    found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'tick':
            if 'prepare_fit_photo' not in ast.unparse(node):
                for block in ast.walk(node):
                    if not isinstance(block, ast.If):
                        continue
                    for index, statement in enumerate(block.body):
                        if isinstance(statement, ast.Assign) and ast.unparse(statement.value) == '(self.photo.width(), self.photo.height())':
                            block.body[index:index] = ast.parse("if hasattr(self, 'prepare_fit_photo'): self.prepare_fit_photo(w, h)").body
                            found = True
                            break
            else:
                found = True
    if not found:
        raise RuntimeError('Geometria do overlay não reconhecida.')
    ast.fix_missing_locations(tree);changes['mapa_overlay.py'] = ast.unparse(tree)+'\n'
    tree = ast.parse((root/'gerar_instalador.py').read_text(encoding='utf-8-sig'));found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            values = [n.value for n in node.elts if isinstance(n, ast.Constant) and isinstance(n.value, str)]
            if 'painel_jogadores.py' in values and 'central_replay.py' in values:
                if 'enquadramento_035.py' not in values:
                    node.elts.append(ast.Constant('enquadramento_035.py'))
                found = True
    if not found:
        raise RuntimeError('Gerador não reconhecido.')
    ast.fix_missing_locations(tree);changes['gerar_instalador.py'] = ast.unparse(tree)+'\n'
    for name, text in changes.items():
        ast.parse(text, filename=name)
    backup = root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    for name in changes:
        shutil.copy2(root/name, backup/name)
    for name, text in changes.items():
        (root/name).write_text(text, encoding='utf-8')
    print('Enquadramento do minimapa instalado. Backup:', backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.3.5 ou superior à última gerada.')


if __name__ == '__main__':
    try:
        main()
    except Exception as erro:
        print('ERRO:', erro)
        raise SystemExit(1)
