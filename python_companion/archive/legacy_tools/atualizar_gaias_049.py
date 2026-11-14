import ast
import shutil
from datetime import datetime
from pathlib import Path

ICON_HELPER = 'def _icone_gaia_049(symbol, obj, kind, art_map, ns):\n    art = ET.fromstring(\'<g xmlns="\' + ns + \'">\' + art_map[kind(obj)] + \'</g>\')\n    for color, width in ((\'#151b18\', \'3.5\'), (\'#fff0be\', \'1.7\')):\n        contour = copy.deepcopy(art)\n        contour.set(\'data-gaia-outline\', color)\n        for shape in contour.iter():\n            if shape.tag.rsplit(\'}\', 1)[-1] in (\'g\', \'title\', \'desc\'):\n                continue\n            if shape.get(\'fill\') != \'none\':\n                shape.set(\'fill\', color)\n            shape.set(\'stroke\', color)\n            shape.set(\'stroke-width\', width)\n            shape.set(\'stroke-linejoin\', \'round\')\n            shape.set(\'stroke-linecap\', \'round\')\n        symbol.append(contour)\n    symbol.append(art)\n'

OCULTAR = ('hawk','vulture','crocodile','wolf','bactrian_camel','bear','lion','tiger','snow_leopard','snake','camel','leopard','black_panther','monkey')


def adaptar(codigo):
    tree=ast.parse(codigo)
    if not any(isinstance(n,ast.FunctionDef) and n.name=='_especie_gaia_044' for n in tree.body):
        raise RuntimeError('Aplique primeiro a atualização 0.4.4 de identificação dos animais.')
    tree.body[:]=[n for n in tree.body if not (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_GAIA_OCULTAS_045' for t in n.targets))]
    tree.body.insert(0,ast.parse('_GAIA_OCULTAS_045 = '+repr(OCULTAR)).body[0])
    aliases = next((n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_GAIA_NAMES_044' for t in n.targets)), None)
    if aliases is None or not isinstance(aliases.value, ast.Dict):
        raise RuntimeError('Dicionário de espécies não reconhecido.')
    names = ast.literal_eval(aliases.value)
    names.update({'cobra': 'snake', 'snake': 'snake', 'serpente': 'snake', 'camelo selvagem': 'camel', 'black panther': 'black_panther', 'pantera negra': 'black_panther', 'monkey': 'monkey', 'macaco': 'monkey', 'tapir': 'boar', 'anta': 'boar'})
    aliases.value = ast.parse(repr(names), mode='eval').body
    found=False
    for function in ast.walk(tree):
        if not isinstance(function,ast.FunctionDef) or function.name!='render':continue
        for node in ast.walk(function):
            if not isinstance(node,ast.For) or ast.unparse(node.iter)!='clusters(neutral)':continue
            if '_GAIA_OCULTAS_045' not in ast.unparse(node):
                index=next((i for i,n in enumerate(node.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='obj' for t in n.targets)),None)
                if index is None:raise RuntimeError('Agrupamento Gaia não reconhecido.')
                node.body[index+1:index+1]=ast.parse('if kind(obj) in _GAIA_OCULTAS_045: continue').body
            found=True
    if not found:raise RuntimeError('Renderização dos animais não reconhecida.')
    tree.body[:] = [n for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == '_icone_gaia_049')]
    tree.body.append(ast.parse(ICON_HELPER).body[0])
    patched = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.If) or ast.unparse(node.test) != 'ident not in embedded':
            continue
        node.body = ast.parse("symbol = ET.SubElement(defs, '{' + ns + '}g', {'id': key})\n_icone_gaia_049(symbol, obj, kind, ART, ns)\nembedded.add(ident)").body
        patched = True
    if not patched:
        raise RuntimeError('Bloco dos ícones Gaia não reconhecido.')
    ast.fix_missing_locations(tree)
    result=ast.unparse(tree)+'\n';ast.parse(result)
    return result


def main():
    root=Path(__file__).resolve().parent
    path=root/'gaia_minimapa.py'
    if not path.is_file():raise RuntimeError('Salve este atualizador na pasta GeradorMapaAoE2, junto de gaia_minimapa.py.')
    result=adaptar(path.read_text(encoding='utf-8-sig'))
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    shutil.copy2(path,backup/path.name)
    path.write_text(result,encoding='utf-8')
    print('Ícones Gaia sem fundo, com contorno; Pantera negra e Macaco ocultos; Tapir com ícone de Javali. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.4.9, ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
