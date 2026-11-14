import base64,hashlib,json,re
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .config import APP,REPOSITORY
from .common import version

MAX_MANIFEST=512*1024
MAX_ASSET=2*1024**3


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def key_id(raw):return hashlib.sha256(raw).hexdigest()[:24]


def validate_payload(value):
    if not isinstance(value,dict) or value.get('schema')!=2 or value.get('app')!=APP or value.get('repository')!=REPOSITORY:
        raise ValueError('Canal de atualização incompatível.')
    version(value['version'])
    if not isinstance(value.get('packages'),list) or not 1<=len(value['packages'])<=50:
        raise ValueError('Catálogo de pacotes inválido.')
    seen=set();full=0
    for package in value['packages']:
        if package.get('kind') not in ('patch','full'):raise ValueError('Tipo de pacote inválido.')
        name=package['filename']
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.aoe2patch',name):
            raise ValueError('Nome de pacote inválido.')
        if name.casefold() in seen:raise ValueError('Nome de pacote duplicado.')
        seen.add(name.casefold())
        prefix=f'https://github.com/{REPOSITORY}/releases/download/v{value["version"]}/'
        if package['url']!=prefix+name:raise ValueError('Pacote fora do repositório oficial.')
        for field in ('sha256','target_fingerprint'):
            if not re.fullmatch(r'[a-f0-9]{64}',package.get(field,'')):raise ValueError('Hash inválido.')
        if package.get('version')!=value['version']:raise ValueError('Versões não correspondem.')
        if type(package.get('size')) is not int or not 0<package['size']<=MAX_ASSET:raise ValueError('Tamanho inválido.')
        if package['kind']=='patch':
            version(package['base_version'])
            if version(package['base_version'])>=version(value['version']):raise ValueError('Base de patch inválida.')
            if not re.fullmatch(r'[a-f0-9]{64}',package.get('base_fingerprint','')):raise ValueError('Base inválida.')
        else:full+=1
    if full>1:raise ValueError('Mais de um pacote completo no catálogo.')
    if not isinstance(value.get('notes',''),str) or len(value.get('notes',''))>10000:raise ValueError('Notas inválidas.')
    return value


def verify(raw,keys=None):
    if len(raw)>MAX_MANIFEST:raise ValueError('Manifesto muito grande.')
    from .trusted_keys import PUBLIC_KEYS
    keys=PUBLIC_KEYS if keys is None else keys
    if not keys:raise ValueError('Canal ainda não configurado pelo publicador: falta a chave pública.')
    envelope=json.loads(raw.decode('utf-8'))
    if envelope.get('format')!=1 or envelope.get('key_id') not in keys:raise ValueError('Assinatura de publicador não reconhecida.')
    try:
        public=base64.b64decode(keys[envelope['key_id']],validate=True)
        signature=base64.b64decode(envelope['signature'],validate=True)
        Ed25519PublicKey.from_public_bytes(public).verify(signature,canonical(envelope['payload']))
    except (ValueError,InvalidSignature,KeyError) as exc:raise ValueError('Assinatura digital inválida.') from exc
    return validate_payload(envelope['payload'])
