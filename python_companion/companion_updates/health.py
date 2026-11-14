import os,re
from .common import data_dir,write_json


def marker(token):
    if not isinstance(token,str) or not re.fullmatch(r'[a-f0-9]{32}',token):raise ValueError('Token de inicialização inválido.')
    return data_dir()/'updates_health'/(token+'.json')


def acknowledge(version):
    token=os.environ.get('AOE2_COMPANION_UPDATE_TOKEN')
    if token:write_json(marker(token),{'token':token,'version':version,'started':True})
