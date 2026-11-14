"""Publisher-only Ed25519 key management. Private material never enters the build."""
from pathlib import Path
import argparse,base64,json,os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from companion_updates.security import canonical,key_id

ROOT=Path(__file__).resolve().parents[1]


def private_path():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AoE2CompanionPublisher/keys/ed25519-private.pem'


def load_private(path=None):
    secret=os.environ.get('COMPANION_SIGNING_KEY_PEM')
    raw=secret.encode('utf-8') if secret else Path(path or private_path()).read_bytes()
    key=serialization.load_pem_private_key(raw,password=None)
    if not isinstance(key,Ed25519PrivateKey):raise ValueError('A chave deve ser Ed25519.')
    return key


def public_entry(key):
    raw=key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
    return key_id(raw),base64.b64encode(raw).decode('ascii')


def initialize(path=None,public_file=None):
    path=Path(path or private_path());public_file=Path(public_file or ROOT/'companion_updates/trusted_keys.py')
    if not path.exists():
        path.parent.mkdir(parents=True,exist_ok=True)
        key=Ed25519PrivateKey.generate()
        raw=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'wb') as f:f.write(raw)
    key=load_private(path);ident,public=public_entry(key)
    # Preserve already trusted public keys when adding a rotation key.
    import ast
    ring={}
    if public_file.exists():
        tree=ast.parse(public_file.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PUBLIC_KEYS' for t in node.targets):ring=ast.literal_eval(node.value)
    ring[ident]=public
    public_file.parent.mkdir(parents=True,exist_ok=True)
    public_file.write_text('"""Public verification keys. Private signing material is stored outside this repository."""\nPUBLIC_KEYS = '+repr(ring)+'\n',encoding='utf-8')
    return ident


def sign(payload,key=None):
    key=key or load_private();ident,_=public_entry(key)
    return {'format':1,'key_id':ident,'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode('ascii')}


def main():
    parser=argparse.ArgumentParser(description='Cria a chave privada fora do projeto e configura somente a chave pública no código.')
    parser.add_argument('command',choices=['init']);args=parser.parse_args()
    ident=initialize();print('Chave pública configurada:',ident)
    print('Chave privada guardada fora do projeto. Faça backup seguro dela; não a envie ao GitHub nem aos compradores.')
if __name__=='__main__':main()
