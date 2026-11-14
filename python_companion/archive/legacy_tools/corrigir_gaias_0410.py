import ast
import shutil
from pathlib import Path
from datetime import datetime

IDS = {2096: 'monkey', 2595: 'black_panther', 2589: 'boar', 2592: 'snake', 1056: 'hawk', 2089: 'bear', 2090: 'bear', 2091: 'wolf', 1965: 'wolf', 2092: 'horse', 2093: 'horse', 2094: 'horse', 2095: 'horse', 2097: 'penguin', 1796: 'gazelle', 1955: 'fox', 1958: 'fox', 305: 'llama', 1963: 'llama', 2615: 'alpaca', 2590: 'capybara', 2591: 'guanaco', 1245: 'pig'}
NAMES = {'black panther': 'black_panther', 'pantera negra': 'black_panther', 'monkey': 'monkey', 'macaco': 'monkey', 'tapir': 'boar', 'anta': 'boar', 'llama': 'llama', 'lhama': 'llama', 'llama a': 'llama', 'llama b': 'llama', 'capybara': 'capybara', 'capivara': 'capybara', 'guanaco': 'guanaco', 'alpaca': 'alpaca', 'wild alpaca': 'alpaca', 'alpaca selvagem': 'alpaca', 'pig': 'pig', 'porco': 'pig'}
ART_EXTRA = {'llama': '<path d="M8 40L10 26L23 25L24 14L22 4L27 5L29 14L32 4L36 4L36 17L33 24L34 38L29 43L16 43Z" fill="#d5bb91"/><path d="M25 18L39 18L40 24L31 28L25 26Z" fill="#ead5af"/><circle cx="32" cy="19" r="1.6" fill="#252b23"/><path d="M12 32L11 44M24 34L24 44" stroke="#997b54" stroke-width="4"/>', 'guanaco': '<path d="M6 33L9 23L23 23L25 12L24 3L28 4L30 12L34 3L37 4L35 17L39 18L40 24L32 27L31 34L28 44L24 44L25 33L14 33L12 44L8 44L9 32Z" fill="#b77f4d"/><path d="M26 22L32 23L30 34L13 33L13 29L25 29Z" fill="#efe0bd"/><circle cx="33" cy="18" r="1.5" fill="#262c26"/>', 'capybara': '<ellipse cx="22" cy="28" rx="19" ry="13" fill="#94734e"/><path d="M8 31L8 42L14 42L15 33M28 33L29 42L35 42L36 31" fill="#6f583d"/><rect x="23" y="16" width="22" height="18" rx="6" fill="#b28b5f"/><ellipse cx="28" cy="15" rx="4" ry="5" fill="#75583d"/><circle cx="36" cy="22" r="1.7" fill="#18231a"/><path d="M40 29L44 29" stroke="#51422e" stroke-width="2"/>', 'pig': '<ellipse cx="24" cy="28" rx="17" ry="14" fill="#dbab9a"/><path d="M11 21L8 8L21 18M28 18L40 8L38 24" fill="#b87f77"/><ellipse cx="31" cy="34" rx="11" ry="7" fill="#edc1af"/><circle cx="28" cy="34" r="1.7" fill="#725147"/><circle cx="35" cy="34" r="1.7" fill="#725147"/><circle cx="21" cy="24" r="1.7" fill="#262c24"/>', 'alpaca': '<path d="M8 40L10 26L23 25L24 14L22 4L27 5L29 14L32 4L36 4L36 17L33 24L34 38L29 43L16 43Z" fill="#eee0c8"/><path d="M25 18L39 18L40 24L31 28L25 26Z" fill="#faf0db"/><circle cx="32" cy="19" r="1.6" fill="#252b23"/><path d="M12 32L11 44M24 34L24 44" stroke="#997b54" stroke-width="4"/>'}
HELPER = 'def _icone_gaia_049(symbol, obj, kind, art_map, ns, images=None):\n    species = kind(obj)\n    raw = (images or {}).get(obj[\'type_id\']) if species == \'neutral\' else None\n    if raw:\n        ET.SubElement(symbol, \'{\' + ns + \'}image\', {\'width\': \'48\', \'height\': \'48\', \'href\': \'data:image/png;base64,\' + base64.b64encode(raw).decode()})\n        return\n    art = ET.fromstring(\'<g xmlns="\' + ns + \'">\' + art_map.get(species, art_map[\'neutral\']) + \'</g>\')\n    for color, width in ((\'#151b18\', \'3.5\'), (\'#fff0be\', \'1.7\')):\n        contour = copy.deepcopy(art)\n        contour.set(\'data-gaia-outline\', color)\n        for shape in contour.iter():\n            if shape.tag.rsplit(\'}\', 1)[-1] in (\'g\', \'title\', \'desc\'):\n                continue\n            if shape.get(\'fill\') != \'none\':\n                shape.set(\'fill\', color)\n            shape.set(\'stroke\', color)\n            shape.set(\'stroke-width\', width)\n            shape.set(\'stroke-linejoin\', \'round\')\n            shape.set(\'stroke-linecap\', \'round\')\n        symbol.append(contour)\n    symbol.append(art)\n'


def adaptar(source):
    tree = ast.parse(source)
    wanted = {'_GAIA_IDS_044': IDS, '_GAIA_NAMES_044': NAMES, '_GAIA_ART_044': ART_EXTRA}
    found = set()
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in wanted:
                value = ast.literal_eval(node.value)
                value.update(wanted[target.id])
                node.value = ast.parse(repr(value), mode='eval').body
                found.add(target.id)
    if found != set(wanted):
        raise RuntimeError('Catálogo Gaia não reconhecido. Nenhum arquivo foi alterado.')
    function = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_icone_gaia_049'), None)
    if function is None:
        raise RuntimeError('Este reparo requer a atualização 0.4.9.')
    tree.body[tree.body.index(function)] = ast.parse(HELPER).body[0]
    calls = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '_icone_gaia_049':
            node.args = ast.parse('_icone_gaia_049(symbol, obj, kind, ART, ns, t.ICONS.images)',mode='eval').body.args
            calls += 1
    if calls != 1:
        raise RuntimeError('Renderizador Gaia não reconhecido. Nenhum arquivo foi alterado.')
    hidden = next((n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_GAIA_OCULTAS_045' for t in n.targets)), None)
    if hidden is None:
        raise RuntimeError('Filtro Gaia não reconhecido.')
    values = list(ast.literal_eval(hidden.value))
    for species in ('black_panther', 'monkey', 'snake', 'camel', 'leopard'):
        if species not in values:
            values.append(species)
    hidden.value = ast.parse(repr(tuple(values)),mode='eval').body
    ast.fix_missing_locations(tree)
    result = ast.unparse(tree) + '\n'
    compile(result, 'gaia_minimapa.py', 'exec')
    return result


def main():
    root = Path(__file__).resolve().parent
    path = root / 'gaia_minimapa.py'
    if not path.is_file():
        raise RuntimeError('Extraia este atualizador na pasta GeradorMapaAoE2, junto de gaia_minimapa.py.')
    result = adaptar(path.read_text(encoding='utf-8-sig'))
    backup = root / 'backups_atualizacoes' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    shutil.copy2(path, backup / path.name)
    path.write_text(result, encoding='utf-8')
    print('Correção Gaia 0.4.10 aplicada. Backup:', backup)
    print('Execute py -3.12 gerar_atualizacao.py e gere versão 0.4.10 ou superior à última gerada.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('ERRO:', error)
        raise SystemExit(1)
