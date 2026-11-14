import ast
import shutil
from pathlib import Path
from datetime import datetime

HELPER = "def _marca_minimapa_0415(root):\n    tag = '{' + NS + '}'\n    for node in list(root):\n        if node.get('id') == 'aoe2-brand-0415':\n            root.remove(node)\n    group = ET.SubElement(root, tag + 'g', {\n        'id': 'aoe2-brand-0415',\n        'transform': 'translate(66 192) rotate(-26.5650511771)',\n        'pointer-events': 'none',\n        'shape-rendering': 'geometricPrecision',\n        'opacity': '0.96',\n        'aria-label': 'AoE II · Replay Companion',\n    })\n    ET.SubElement(group, tag + 'title').text = 'AoE II · Replay Companion'\n    ET.SubElement(group, tag + 'path', {\n        'd': 'M-9 -6L-5 -10L-1 -6L-5 -2Z',\n        'fill': '#d8b77c', 'stroke': '#18201b', 'stroke-width': '0.8',\n    })\n    ET.SubElement(group, tag + 'text', {\n        'x': '4', 'y': '0',\n        'font-family': 'Georgia, Cambria, Times New Roman, serif',\n        'font-size': '17', 'font-weight': 'bold',\n        'letter-spacing': '0.35',\n        'fill': '#d8b77c',\n        'stroke': '#18201b', 'stroke-width': '0.55',\n        'paint-order': 'stroke fill',\n        'text-rendering': 'optimizeLegibility',\n    }).text = 'AoE II · Replay Companion'\n"


def adaptar(source):
    tree = ast.parse(source)
    target = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'minimap_svg'), None)
    if target is None:
        raise RuntimeError('Renderizador minimap_svg não encontrado. Nenhum arquivo foi alterado.')
    returns = [n for n in target.body if isinstance(n, ast.Return)]
    if len(returns) != 1 or 'ET.tostring(root' not in ast.unparse(returns[0]):
        raise RuntimeError('Saída do minimapa não reconhecida. Nenhum arquivo foi alterado.')
    target.body[:] = [n for n in target.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Name) and n.value.func.id == '_marca_minimapa_0415')]
    target.body.insert(target.body.index(returns[0]), ast.parse('_marca_minimapa_0415(root)').body[0])
    tree.body[:] = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == '_marca_minimapa_0415')]
    tree.body.insert(tree.body.index(target), ast.parse(HELPER).body[0])
    ast.fix_missing_locations(tree)
    result = ast.unparse(tree) + '\n'
    compile(result, 'minimapa_aoe2.py', 'exec')
    return result


def main():
    root = Path(__file__).resolve().parent
    path = root / 'minimapa_aoe2.py'
    if not path.is_file():
        raise RuntimeError('Extraia este atualizador na pasta GeradorMapaAoE2, junto de minimapa_aoe2.py.')
    result = adaptar(path.read_text(encoding='utf-8-sig'))
    backup = root / 'backups_atualizacoes' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    shutil.copy2(path, backup / path.name)
    try:
        path.write_text(result, encoding='utf-8')
    except Exception:
        shutil.copy2(backup / path.name, path)
        raise
    print('Assinatura AoE II · Replay Companion aplicada ao minimapa. Backup:', backup)
    print('Execute py -3.12 gerar_atualizacao.py. Use versão 0.4.15 ou superior à última gerada.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERRO:', error)
        raise SystemExit(1)
