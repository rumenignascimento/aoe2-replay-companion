from pathlib import Path
import json,os,re,sys,uuid


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):
        raise ValueError('Versão inválida; use três números, por exemplo 0.5.0.')
    return tuple(map(int,value.split('.')))


def data_dir():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AoE2Overlay'


def install_dir():
    if getattr(sys,'frozen',False):return Path(sys.executable).parent
    return Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Programs/AoE2Overlay'


def read_json(path,default=None):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default


def write_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('w',encoding='utf-8') as f:
            json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)


def installed_version(root):
    for name in ('build-info.json','.patch_state.json'):
        value=read_json(Path(root)/name,{})
        try:version(value.get('version'));return value['version']
        except (ValueError,AttributeError):pass
    return None


def settings():
    stored=read_json(data_dir()/'update_settings.json',{})
    return {'auto_check':stored.get('auto_check',True) is True,
            'auto_download':stored.get('auto_download',True) is True}
