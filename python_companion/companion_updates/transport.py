from pathlib import Path
import hashlib,os,urllib.request,urllib.error,uuid
from urllib.parse import urlsplit
from .security import MAX_MANIFEST
from .config import MANIFEST_URL


def safe_url(url):
    p=urlsplit(url)
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443):raise ValueError('Endereço de atualização inválido.')
    host=p.hostname or ''
    if host not in ('github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'):
        raise ValueError('Servidor de atualização inesperado.')
    return url

class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        safe_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def open_url(url,headers=None):
    safe_url(url)
    request=urllib.request.Request(url,headers={'User-Agent':'AoE2-Replay-Companion/updates','Accept-Encoding':'identity',**(headers or {})})
    return urllib.request.build_opener(Redirect()).open(request,timeout=30)


def fetch_manifest():
    with open_url(MANIFEST_URL) as response:raw=response.read(MAX_MANIFEST+1)
    if len(raw)>MAX_MANIFEST:raise ValueError('Manifesto excessivamente grande.')
    return raw


def download(package,directory,progress=None,cancel=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    target=directory/package['filename']
    if target.is_file() and file_hash(target)==package['sha256'] and target.stat().st_size==package['size']:return target
    temp=target.with_name(target.name+'.'+uuid.uuid4().hex+'.download')
    try:
        h=hashlib.sha256();count=0
        with open_url(package['url']) as response,temp.open('wb') as out:
            safe_url(response.geturl())
            for chunk in iter(lambda:response.read(1024*1024),b''):
                if cancel is not None and cancel.is_set():raise InterruptedError('Download cancelado.')
                count+=len(chunk)
                if count>package['size']:raise ValueError('Download excede o tamanho assinado.')
                h.update(chunk);out.write(chunk)
                if progress:progress(count,package['size'])
            out.flush();os.fsync(out.fileno())
        if count!=package['size'] or h.hexdigest()!=package['sha256']:raise ValueError('Download incompleto ou corrompido.')
        os.replace(temp,target);return target
    finally:temp.unlink(missing_ok=True)


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
