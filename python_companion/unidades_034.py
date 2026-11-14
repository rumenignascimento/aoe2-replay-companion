"""Correspondência exata de unidades e ícones; sem inferência por nome ou edifício."""
import base64
import hashlib
import json
from unidades_assets_034 import CATALOG, PICTURES, SOURCE_COMMIT

_VERIFIED = {}
_ERRORS = set()


def _error(icons, text):
    if text not in _ERRORS:
        _ERRORS.add(text)
        icons.errors.append(text)


def preparar(session, g):
    t = g['t']
    icons = t.ICONS
    # Estes arquivos também são usados pelo módulo de pesquisas.
    icons.tree('BRITONS')
    for player in session.model.get('players', []):
        icons.tree(player['civilization'])
    # Um catálogo único por ID impede que nomes parecidos sirvam como aliases.
    icons.data.update({ident: dict(record) for ident, record in CATALOG.items()})
    kinds = {int(o['type_id']) for o in session.initial if o['kind'] == 'unit' and o.get('owner', 0) > 0}
    for counts in getattr(session, 'all_production', {}).values():
        kinds.update(counts)
    kinds.update(getattr(session, 'military_production_orders', {}))
    missing = []
    repairs = []
    for ident in sorted(kinds):
        record = CATALOG.get(ident)
        if record is None:
            if ident not in t.CIVILIAN_IDS:
                icons.data.pop(ident, None)
                icons.images.pop(ident, None)
                missing.append(ident)
            continue
        if not icons.military(ident):
            continue
        picture = PICTURES[record['picture']]
        path = t.ROOT / 'icones_aoe2' / f'troop_{ident}.png'
        try:
            stat = path.stat() if path.exists() else None
            stamp = (stat.st_mtime_ns, stat.st_size, picture['sha256']) if stat else None
            if stamp is not None and _VERIFIED.get(str(path)) == stamp and ident in icons.images:
                continue
            data = path.read_bytes() if stat else b''
            if hashlib.sha256(data).hexdigest() != picture['sha256']:
                data = base64.b64decode(picture['base64'], validate=True)
                if hashlib.sha256(data).hexdigest() != picture['sha256']:
                    raise ValueError('Hash do pacote de ícones inválido.')
                t.atomic_write(path, data)
                repairs.append(ident)
            icons.images[ident] = data
            icons.attempted.add(ident)
            stat = path.stat()
            _VERIFIED[str(path)] = (stat.st_mtime_ns, stat.st_size, picture['sha256'])
        except (OSError, ValueError) as error:
            icons.images.pop(ident, None)
            _error(icons, f'Unidade ID {ident}: {error}')
    for ident in missing:
        _error(icons, f'Unidade ID {ident} sem correspondência exata no catálogo {SOURCE_COMMIT}. Não recebeu ícone de outro tipo.')
    report = {
        'source_commit': SOURCE_COMMIT,
        'catalog_unit_ids': len(CATALOG),
        'unmapped_unit_ids': missing,
        'observed_unit_ids': sorted(kinds),
        'counts_meaning': 'recorded_production_commands_not_live_units',
    }
    # Evita gravar o mesmo relatório em cada ciclo de renderização.
    report_path = t.ROOT / 'auditoria_unidades_034.json'
    previous = getattr(icons, '_unit_audit', None)
    if previous != report or repairs:
        try:
            t.atomic_write(report_path, json.dumps(dict(report, repaired_icon_ids=repairs), ensure_ascii=False, indent=2).encode('utf-8'))
            icons._unit_audit = report
        except OSError as error:
            _error(icons, 'Não foi possível gravar a auditoria de unidades: ' + str(error))
