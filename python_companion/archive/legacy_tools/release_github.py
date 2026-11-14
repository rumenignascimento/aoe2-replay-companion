"""Preparação local de Release pública. Não faz upload nem usa credenciais."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,zipfile

DEFAULT_REPO='rumenignascimento/aoe2-companion-updates'

def repository(value):
    value=value.strip().removeprefix('https://github.com/').rstrip('/').removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]+',value):raise ValueError('Use usuario/repositorio ou a URL do GitHub.')
    return value

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def prepare(patch,updater,repo,dest):
    repo=repository(repo);patch=Path(patch);updater=Path(updater)
    if not updater.is_file() or updater.suffix.lower()!='.exe':raise ValueError('Selecione AtualizadorAoE2.exe compilado com o aplicador novo.')
    with zipfile.ZipFile(patch) as z:
        if z.getinfo('manifest.json').file_size>10*1024*1024:raise ValueError('Manifesto excessivo.')
        manifest=json.loads(z.read('manifest.json'))
    if manifest.get('format')!=1 or manifest.get('app')!='AoE2Overlay':raise ValueError('Patch incompatível.')
    version=manifest['version'];base=manifest['base_version']
    if not all(re.fullmatch(r'\d+\.\d+\.\d+',v) for v in (version,base)):raise ValueError('Versões inválidas.')
    for field in ('base_fingerprint','target_fingerprint'):
        if not re.fullmatch(r'[a-f0-9]{64}',manifest[field]):raise ValueError('Fingerprint inválido.')
    target=Path(dest)/('v'+version)
    if target.exists():raise ValueError('A pasta de publicação já existe: '+str(target)+'. Preserve releases publicadas; use outra pasta para preparar novamente.')
    target.mkdir(parents=True)
    try:
        patch_name='AoE2Overlay-'+version+'.aoe2patch';updater_name='AtualizadorAoE2.exe'
        shutil.copy2(patch,target/patch_name);shutil.copy2(updater,target/updater_name)
        prefix='https://github.com/'+repo+'/releases/download/v'+version+'/'
        def asset(name):
            p=target/name
            return {'filename':name,'url':prefix+name,'sha256':digest(p),'size':p.stat().st_size}
        data={'schema':1,'app':'AoE2Overlay','repository':repo,'version':version,'base_version':base,
              'base_fingerprint':manifest['base_fingerprint'],'target_fingerprint':manifest['target_fingerprint'],
              'patch':asset(patch_name),'updater':asset(updater_name)}
        (target/'atualizacao.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        (target/'NOTAS_RELEASE.txt').write_text('AoE II · Replay Companion '+version+'\n\nAtualização da versão '+base+' para '+version+'.\n\nFeche o Companion antes de aplicar o patch. Use AtualizadorAoE2.exe para selecionar a instalação e o arquivo .aoe2patch.\nConfigurações são preservadas; há restauração da versão anterior.\n\nAcrescente aqui as novidades desta versão antes de publicar.\n',encoding='utf-8')
        (target/'PUBLICAR.txt').write_text('Abra https://github.com/'+repo+'/releases/new\nTag: v'+version+'\nTítulo: AoE II Replay Companion '+version+'\nCole as notas revisadas.\nAnexe SOMENTE: atualizacao.json, '+patch_name+' e '+updater_name+'.\nNão marque pre-release. Revise e clique Publish release.\nNão envie a pasta GeradorMapaAoE2, códigos Python, compilações ou saves.\n',encoding='utf-8')
        return target,data
    except Exception:
        shutil.rmtree(target);raise

def main():
    p=argparse.ArgumentParser(description='Prepara arquivos para GitHub Releases, sem publicá-los.')
    p.add_argument('--repo',default=DEFAULT_REPO);p.add_argument('--patch',type=Path);p.add_argument('--aplicador',type=Path);p.add_argument('--saida',type=Path,default=Path.cwd()/'publicacao_github')
    args=p.parse_args()
    if not args.patch or not args.aplicador:
        import tkinter as tk
        from tkinter import filedialog
        root=tk.Tk();root.withdraw()
        try:
            if not args.patch:
                value=filedialog.askopenfilename(title='Escolha o patch .aoe2patch para publicar',filetypes=[('Patch AoE II','*.aoe2patch')]);args.patch=Path(value) if value else None
            if not args.aplicador:
                value=filedialog.askopenfilename(title='Escolha AtualizadorAoE2.exe compilado com o aplicador novo',filetypes=[('Executável','*.exe')]);args.aplicador=Path(value) if value else None
        finally:root.destroy()
    if not args.patch or not args.aplicador:raise ValueError('Seleção cancelada.')
    folder,data=prepare(args.patch,args.aplicador,args.repo,args.saida)
    print('Arquivos preparados:',folder)
    print('Nada foi publicado. Siga PUBLICAR.txt e revise NOTAS_RELEASE.txt.')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
