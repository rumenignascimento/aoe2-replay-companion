import ast
import shutil
from pathlib import Path
from datetime import datetime

HELPER = 'def _estado_gaia_0417(session):\n    import threading\n    state = getattr(session, \'_gaia_state_0417\', None)\n    header = getattr(session, \'header\', None)\n    dimension = getattr(session, \'model\', {}).get(\'dimension\')\n    if header is None or not isinstance(dimension, (int, float)):\n        return None\n    if state is not None and state[\'header\'] is header:\n        return state\n    initial = {}\n    for player in header.get(\'players\', ()):\n        if player.get(\'number\') != 0:\n            continue\n        for raw in player.get(\'objects\', ()):\n            if raw.get(\'class_id\') != 70:\n                continue\n            probe = {\'type_id\': raw.get(\'object_id\'), \'name\': \'\'}\n            category = _gaia_categoria_0414(probe)\n            if category is None or category[1] == \'reliquia\':\n                continue\n            ident = raw.get(\'instance_id\')\n            if isinstance(ident, int):\n                initial[ident] = raw.get(\'object_id\')\n    state = {\'header\': header, \'initial\': initial, \'positions\': {}, \'requests\': {},\n             \'last\': None, \'clock\': -1, \'observations\': 0, \'move_orders\': 0,\n             \'lock\': threading.RLock()}\n    session._gaia_state_0417 = state\n    return state\n\n\ndef _observar_gaia_0417(session, action, payload):\n    import math\n    if not isinstance(payload, dict):\n        return\n    state = _estado_gaia_0417(session)\n    if state is None:\n        return\n    name = getattr(action, \'name\', str(action)).rsplit(\'.\', 1)[-1].upper()\n    if name not in (\'ORDER\', \'GATHER_POINT\', \'MOVE\', \'PATROL\', \'DE_ATTACK_MOVE\', \'STOP\'):\n        return\n    ms = getattr(session, \'ms\', 0)\n    if not isinstance(ms, (int, float)) or not math.isfinite(ms):\n        return\n    ids = tuple(i for i in payload.get(\'object_ids\', ()) if isinstance(i, int))\n    x, y = payload.get(\'x\'), payload.get(\'y\')\n    dimension = session.model[\'dimension\']\n    valid = all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and 0 <= v < dimension for v in (x, y))\n    signature = (ms, name, payload.get(\'sequence\'), payload.get(\'target_id\'), ids, x, y)\n    with state[\'lock\']:\n        if ms < state[\'clock\']:\n            state[\'positions\'].clear()\n            state[\'requests\'].clear()\n            state[\'last\'] = None\n        state[\'clock\'] = ms\n        if signature == state[\'last\']:\n            return\n        state[\'last\'] = signature\n        target = payload.get(\'target_id\')\n        if name in (\'ORDER\', \'GATHER_POINT\') and target in state[\'initial\'] and valid:\n            target_type = payload.get(\'target_type\')\n            if target_type is not None and target_type != state[\'initial\'][target]:\n                return\n            state[\'positions\'][target] = (float(x), float(y), ms, name)\n            state[\'requests\'].pop(target, None)\n            state[\'observations\'] += 1\n        elif name in (\'MOVE\', \'PATROL\', \'DE_ATTACK_MOVE\') or (name == \'ORDER\' and target in (-1, 0xffffffff)):\n            if not valid:\n                return\n            for ident in ids:\n                if ident in state[\'initial\']:\n                    # This is only a request; never promote a destination to a position.\n                    state[\'requests\'][ident] = (float(x), float(y), ms)\n                    state[\'move_orders\'] += 1\n        elif name == \'STOP\':\n            for ident in ids:\n                state[\'requests\'].pop(ident, None)\n\n\ndef _referencias_gaia_0417(session, records):\n    state = _estado_gaia_0417(session)\n    if state is None:\n        return records\n    with state[\'lock\']:\n        positions = dict(state[\'positions\'])\n        requests = dict(state[\'requests\'])\n    result = []\n    for obj in records:\n        changed = dict(obj)\n        position = positions.get(obj[\'id\'])\n        if position is not None:\n            changed[\'x\'], changed[\'y\'] = position[:2]\n            changed[\'gaia_reference\'] = \'order_target\'\n            changed[\'gaia_reference_ms\'] = position[2]\n            changed[\'gaia_reference_action\'] = position[3]\n        else:\n            changed[\'gaia_reference\'] = \'initial\'\n        if obj[\'id\'] in requests:\n            changed[\'gaia_requested_destination\'] = requests[obj[\'id\']]\n        result.append(changed)\n    return result\n\n\ndef _titulo_gaia_0417(group):\n    observed = [obj for obj in group if obj.get(\'gaia_reference\') == \'order_target\']\n    title = f"Gaia · {group[0][\'name\']} · {len(group)} objeto(s). "\n    if observed:\n        ms = max(obj[\'gaia_reference_ms\'] for obj in observed)\n        minutes, seconds = divmod(int(ms // 1000), 60)\n        title += f\'R = referência do alvo em ordem; registro mais recente em {minutes:02}:{seconds:02}. \'\n        if len(observed) != len(group):\n            title += \'Grupo também contém referências iniciais. \'\n    else:\n        title += \'Posição inicial do replay. \'\n    if any(\'gaia_requested_destination\' in obj for obj in group):\n        title += \'Há destino de deslocamento solicitado; chegada não confirmada. \'\n    return title + \'Posição atual, morte e esgotamento não confirmados.\'\n\n\ndef _instalar_observacao_gaia_0417(g):\n    import functools\n    candidates = []\n    tracker = g.get(\'t\')\n    panel = getattr(tracker, \'panel\', None)\n    for source, key in ((g.get(\'p\'), \'OrderSession\'), (panel, \'OrderSession\')):\n        cls = getattr(source, key, None)\n        if isinstance(cls, type) and callable(getattr(cls, \'apply\', None)) and cls not in candidates:\n            candidates.append(cls)\n    cls = g.get(\'Session\')\n    if isinstance(cls, type) and callable(getattr(cls, \'apply\', None)) and cls not in candidates:\n        candidates.append(cls)\n    if not candidates:\n        raise RuntimeError(\'Não foi possível localizar OrderSession.apply para acompanhar as ordens Gaia.\')\n    for cls in candidates:\n        if cls.__dict__.get(\'_gaia_apply_0417_installed\', False):\n            continue\n        original = cls.apply\n        def wrap(method):\n            @functools.wraps(method)\n            def apply(self, action, payload, *args, **kwargs):\n                result = method(self, action, payload, *args, **kwargs)\n                _observar_gaia_0417(self, action, payload)\n                return result\n            return apply\n        cls.apply = wrap(original)\n        cls._gaia_apply_0417_installed = True\n    g[\'gaia_tracking_info\'] = _estado_gaia_0417\n'


def adaptar(source):
    tree=ast.parse(source)
    activate=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ativar'),None)
    if activate is None:raise RuntimeError('Integração Gaia não reconhecida.')
    if not any(isinstance(n,ast.FunctionDef) and n.name=='_gaia_categoria_0414' for n in tree.body):raise RuntimeError('Aplique primeiro a atualização de Gaia coletáveis 0.4.14.')
    activate.body[:]=[n for n in activate.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='_instalar_observacao_gaia_0417')]
    # Install before claiming successful activation, and before a Window can open a replay.
    index=next((i for i,n in enumerate(activate.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Subscript) and ast.unparse(t)=="g['_gaia_minimapa_ativa']" for t in n.targets)),None)
    if index is None:raise RuntimeError('Controle de ativação Gaia não reconhecido.')
    activate.body.insert(index,ast.parse('_instalar_observacao_gaia_0417(g)').body[0])
    records=next((n for n in activate.body if isinstance(n,ast.FunctionDef) and n.name=='records'),None)
    if records is None:raise RuntimeError('Leitura dos animais não reconhecida.')
    returns=[n for n in records.body if isinstance(n,ast.Return)]
    if len(returns)!=1:raise RuntimeError('Saída da leitura Gaia não reconhecida.')
    returns[0].value=ast.parse('_referencias_gaia_0417(session, result)',mode='eval').body
    render=next((n for n in activate.body if isinstance(n,ast.FunctionDef) and n.name=='render'),None)
    if render is None:raise RuntimeError('Renderizador Gaia não reconhecido.')
    loop=next((n for n in ast.walk(render) if isinstance(n,ast.For) and ast.unparse(n.iter)=='clusters(neutral)'),None)
    if loop is None:raise RuntimeError('Agrupamento Gaia não reconhecido.')
    titles=0
    for n in ast.walk(loop):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='text' and isinstance(t.value,ast.Call) and any(isinstance(a,ast.Constant) and isinstance(a.value,str) and a.value.endswith('title') for a in ast.walk(t.value)) for t in n.targets):
            n.value=ast.parse('_titulo_gaia_0417(group)',mode='eval').body;titles+=1
    if titles!=1:raise RuntimeError('Legenda descritiva Gaia não reconhecida.')
    for n in ast.walk(loop):
        if isinstance(n,ast.Dict) and any(isinstance(k,ast.Constant) and k.value=='data-gaia' for k in n.keys):
            mapping={k.value:i for i,k in enumerate(n.keys) if isinstance(k,ast.Constant)}
            for key,expr in [('data-reference', "'order_target' if any(m.get('gaia_reference') == 'order_target' for m in group) else 'initial'"),('data-reference-ms', "str(max((m.get('gaia_reference_ms', 0) for m in group), default=0))")]:
                if key in mapping:n.values[mapping[key]]=ast.parse(expr,mode='eval').body
                else:n.keys.append(ast.Constant(value=key));n.values.append(ast.parse(expr,mode='eval').body)
    loop.body[:]=[n for n in loop.body if not (isinstance(n,ast.If) and ast.dump(n.test)==ast.dump(ast.parse("any(m.get('gaia_reference') == 'order_target' for m in group)",mode='eval').body))]
    index=next((i for i,n in enumerate(loop.body) if isinstance(n,ast.If) and ast.unparse(n.test)=='len(group) > 1'),None)
    if index is None:raise RuntimeError('Contagem agrupada Gaia não reconhecida.')
    marker=ast.parse("if any(m.get('gaia_reference') == 'order_target' for m in group):\n    ET.SubElement(node, '{' + ns + '}text', {'x': str(px - size / 2), 'y': str(py - size / 2 + 5), 'fill': '#fff0be', 'stroke': '#142018', 'stroke-width': '0.4', 'font-size': '7', 'font-weight': 'bold', 'font-family': 'Segoe UI,Arial', 'data-gaia-reference-marker': 'R'}).text = 'R'").body[0]
    loop.body.insert(index,marker)
    render.body[:]=[n for n in render.body if not (isinstance(n,ast.If) and 'gaia-reference-legend-0417' in ast.unparse(n))]
    last_return=next(n for n in reversed(render.body) if isinstance(n,ast.Return))
    legend=ast.parse("if any(obj.get('gaia_reference') == 'order_target' for obj in neutral):\n    ET.SubElement(root, '{' + ns + '}text', {'id': 'gaia-reference-legend-0417', 'x': '40', 'y': '430', 'fill': '#d8b77c', 'stroke': '#142018', 'stroke-width': '0.25', 'font-family': 'Segoe UI,Arial', 'font-size': '8'}).text = 'R: referência em ordem · posição atual não confirmada'").body[0]
    render.body.insert(render.body.index(last_return),legend)
    helper_nodes=ast.parse(HELPER).body
    names={n.name for n in helper_nodes if isinstance(n,ast.FunctionDef)}
    tree.body[:]=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name in names)]
    index=tree.body.index(activate);tree.body[index:index]=helper_nodes
    ast.fix_missing_locations(tree)
    result=ast.unparse(tree)+'\n';compile(result,'gaia_minimapa.py','exec');return result


def main():
    root=Path(__file__).resolve().parent;path=root/'gaia_minimapa.py'
    if not path.is_file():raise RuntimeError('Extraia o atualizador na pasta GeradorMapaAoE2, junto de gaia_minimapa.py.')
    result=adaptar(path.read_text(encoding='utf-8-sig'))
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True);shutil.copy2(path,backup/path.name)
    try:path.write_text(result,encoding='utf-8')
    except Exception:
        shutil.copy2(backup/path.name,path);raise
    print('Referências Gaia em ordens integradas ao minimapa. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Use versão 0.4.17 ou superior à última gerada.')
    print('R = referência registrada em ordem; movimento, chegada e esgotamento não são confirmados.')


if __name__=='__main__':
    try:main()
    except Exception as error:
        print('ERRO:',error)
        raise SystemExit(1)
