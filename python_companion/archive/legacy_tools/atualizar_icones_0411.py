import ast
import os
import shutil
from pathlib import Path
from datetime import datetime

HELPER = "from functools import lru_cache as _cache_icone_0411\n\n@_cache_icone_0411(maxsize=512)\ndef _unidade_transparente_0411(raw):\n    import io\n    from collections import deque\n    from PIL import Image, ImageChops, ImageFilter\n    with Image.open(io.BytesIO(raw)) as source:\n        image = source.convert('RGBA')\n    width, height = image.size\n    pixels = image.load()\n    seen = set()\n    queue = deque()\n    def background(x, y):\n        r, g, b, a = pixels[x, y]\n        return a == 0 or (max(r, g, b) <= 16 and max(r, g, b) - min(r, g, b) <= 12)\n    def visit(x, y):\n        if (x, y) not in seen and background(x, y):\n            seen.add((x, y))\n            queue.append((x, y))\n    for x in range(width):\n        visit(x, 0)\n        visit(x, height - 1)\n    for y in range(height):\n        visit(0, y)\n        visit(width - 1, y)\n    while queue:\n        x, y = queue.popleft()\n        r, g, b, a = pixels[x, y]\n        pixels[x, y] = (r, g, b, 0)\n        for xx, yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):\n            if 0 <= xx < width and 0 <= yy < height:\n                visit(xx, yy)\n    padded = Image.new('RGBA', (width+6, height+6))\n    padded.alpha_composite(image, (3,3))\n    alpha = padded.getchannel('A')\n    outer = alpha.filter(ImageFilter.MaxFilter(7))\n    inner = alpha.filter(ImageFilter.MaxFilter(3))\n    result = Image.new('RGBA', padded.size, '#111915')\n    result.putalpha(outer)\n    light = Image.new('RGBA', padded.size, '#fff1bc')\n    light.putalpha(inner)\n    result = Image.alpha_composite(result, light)\n    result = Image.alpha_composite(result, padded)\n    # SVG coordinates remain 48x48 plus the contour margin, independent of source resolution.\n    if result.size != (54, 54):\n        result = result.resize((54,54), Image.Resampling.LANCZOS)\n    output = io.BytesIO()\n    result.save(output, format='PNG')\n    return output.getvalue()\n"


def adaptar_minimapa(source):
    tree=ast.parse(source)
    function=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='minimap_svg'),None)
    if function is None: raise RuntimeError('minimap_svg não encontrado.')
    image_id=next((n for n in function.body if isinstance(n,ast.FunctionDef) and n.name=='image_id'),None)
    if image_id is None: raise RuntimeError('Carregador dos ícones de construção não reconhecido.')
    image_call=next((n for n in ast.walk(image_id) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='add' and len(n.args)>1 and isinstance(n.args[1],ast.Constant) and n.args[1].value=='image'),None)
    if image_call is None: raise RuntimeError('Imagem das construções não reconhecida.')
    if not any(isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='clip_0411' for t in n.targets) for n in image_id.body):
        index=next(i for i,n in enumerate(image_id.body) if isinstance(n,ast.Expr) and n.value is image_call)
        block=ast.parse("clip_0411 = ''\nif ident in app.base.g.TC_IDS or ident in (109,621):\n    clip_0411 = key + '-rounded'\n    clip = add(defs, 'clipPath', id=clip_0411, clipPathUnits='userSpaceOnUse')\n    add(clip, 'rect', x=0, y=0, width=48, height=48, rx=11.5, ry=11.5)").body
        image_id.body[index:index]=block
    image_call.keywords=[k for k in image_call.keywords if not (k.arg is None and isinstance(k.value,ast.Dict) and any(isinstance(key,ast.Constant) and key.value=='clip-path' for key in k.value.keys))]
    image_call.keywords.append(ast.keyword(arg=None,value=ast.parse("{'clip-path': 'url(#' + clip_0411 + ')' if clip_0411 else 'none', 'shape-rendering':'geometricPrecision'}",mode='eval').body))
    borders=0
    for node in ast.walk(function):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name) or node.func.id!='add' or len(node.args)<2:continue
        if not isinstance(node.args[1],ast.Constant) or node.args[1].value!='rect':continue
        if not any(k.arg=='stroke' and isinstance(k.value,ast.Call) and isinstance(k.value.func,ast.Name) and k.value.func.id=='owner_color' for k in node.keywords):continue
        node.keywords=[k for k in node.keywords if k.arg not in ('rx','ry')]
        for key in ('rx','ry'):
            node.keywords.append(ast.keyword(arg=key,value=ast.parse('(size + 2) * 0.24 if ident in app.base.g.TC_IDS or ident in (109,621) else 0',mode='eval').body))
        borders+=1
    if borders!=1:raise RuntimeError('Borda dos ícones de construção não reconhecida.')
    ast.fix_missing_locations(tree)
    result=ast.unparse(tree)+'\n';compile(result,'minimapa_aoe2.py','exec');return result


def adaptar_tropas(source):
    tree=ast.parse(source)
    function=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='movement_map'),None)
    if function is None:raise RuntimeError('Renderizador de deslocamentos não encontrado.')
    calls=0
    for node in ast.walk(function):
        if not isinstance(node,ast.Call) or not isinstance(node.func,ast.Name) or node.func.id!='add' or len(node.args)<2:continue
        if not isinstance(node.args[1],ast.Constant) or node.args[1].value!='image':continue
        for k in node.keywords:
            if k.arg=='href':
                k.value=ast.parse("'data:image/png;base64,' + base64.b64encode(_unidade_transparente_0411(image)).decode('ascii')",mode='eval').body
        node.keywords=[k for k in node.keywords if k.arg not in ('width','height','x','y')]
        node.keywords += [ast.keyword(arg=k,value=ast.Constant(value=v)) for k,v in [('width',54),('height',54),('x',-3),('y',-3)]]
        calls+=1
    if calls!=1:raise RuntimeError('Imagem dos deslocamentos não reconhecida.')
    tree.body[:]=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='_unidade_transparente_0411') and not (isinstance(n,ast.ImportFrom) and any(a.asname=='_cache_icone_0411' for a in n.names))]
    tree.body.extend(ast.parse(HELPER).body)
    ast.fix_missing_locations(tree)
    result=ast.unparse(tree)+'\n';compile(result,'painel_tropas.py','exec');return result


def main():
    root=Path(__file__).resolve().parent
    originals={}
    results={}
    for name,adapt in [('minimapa_aoe2.py',adaptar_minimapa),('painel_tropas.py',adaptar_tropas)]:
        path=root/name
        if not path.is_file():raise RuntimeError('Arquivo ausente: '+name+'. Extraia o atualizador na pasta GeradorMapaAoE2.')
        originals[name]=path.read_bytes()
        results[name]=adapt(originals[name].decode('utf-8-sig'))
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    for name in originals:shutil.copy2(root/name,backup/name)
    try:
        for name,result in results.items():
            temporary=root/(name+'.0411.tmp')
            temporary.write_text(result,encoding='utf-8')
            os.replace(temporary,root/name)
    except Exception:
        for name in originals:shutil.copy2(backup/name,root/name)
        raise
    finally:
        for name in results:(root/(name+'.0411.tmp')).unlink(missing_ok=True)
    print('TC arredondado e unidades militares sem fundo preto, com contorno. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Use versão 0.4.11 ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('ERRO:',error)
        raise SystemExit(1)
