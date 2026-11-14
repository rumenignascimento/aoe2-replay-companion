"""Prepare signed binary assets. Upload a draft only when explicitly requested."""
from pathlib import Path
import argparse,json,os,shutil,subprocess,zipfile
from patch_core import create_patch,sha,inventory
from companion_updates.common import version,installed_version
from companion_updates.config import APP,REPOSITORY
from companion_updates.security import validate_payload,verify
from tools.signing import load_private,sign
from tools.packages import create_full

ROOT=Path(__file__).resolve().parents[1]


def prepare(build,output,base=None,base_version=None,notes='',key=None):
    build=Path(build);current=installed_version(build)
    if not current or not (build/'build-info.json').is_file():raise ValueError('Use o build novo que contém build-info.json.')
    version(current)
    if not (build/'AoE2Updater.exe').is_file():raise ValueError('Build sem aplicador integrado.')
    output=Path(output)/('v'+current)
    if output.exists():raise ValueError('A pasta desta versão já existe. Use outra saída para refazer; não substitua uma versão publicada.')
    output.mkdir(parents=True)
    try:
        packages=[]
        def describe(path,manifest,kind):
            return {'kind':kind,'filename':path.name,'url':f'https://github.com/{REPOSITORY}/releases/download/v{current}/{path.name}',
                    'sha256':sha(path),'size':path.stat().st_size,'version':current,
                    'target_fingerprint':manifest['target_fingerprint'],
                    **({'base_version':manifest['base_version'],'base_fingerprint':manifest['base_fingerprint']} if kind=='patch' else {})}
        full=output/f'AoE2Overlay-{current}-full.aoe2patch'
        packages.append(describe(full,create_full(build,full,current),'full'))
        if base:
            base=Path(base);base_version=base_version or installed_version(base)
            if not base_version:raise ValueError('Informe --base-version para um build legado sem versão registrada.')
            patch_path=output/f'AoE2Overlay-{base_version}-to-{current}.aoe2patch'
            packages.append(describe(patch_path,create_patch(base,build,patch_path,base_version,current),'patch'))
        payload={'schema':2,'app':APP,'repository':REPOSITORY,'version':current,'notes':notes,'packages':packages}
        validate_payload(payload)
        envelope=sign(payload,key)
        build_info=json.loads((build/'build-info.json').read_text(encoding='utf-8'))
        if envelope['key_id'] not in build_info.get('update_key_ids',[]):
            raise ValueError('O build não contém a chave pública que assina esta Release. Recompile após configurar a chave.')
        if base and (base/'build-info.json').is_file():
            base_info=json.loads((base/'build-info.json').read_text(encoding='utf-8'))
            if envelope['key_id'] not in base_info.get('update_key_ids',[]):
                raise ValueError('A base não confia nesta chave. Faça a rotação usando a chave anterior antes de trocar a assinatura.')
        # Ensure the signing key corresponds to a key pinned in the compiled source.
        raw=json.dumps(envelope,ensure_ascii=False,indent=2).encode('utf-8')
        verify(raw)
        (output/'updates.json').write_bytes(raw)
        (output/'NOTAS_RELEASE.md').write_text(notes or 'Atualização do AoE II Replay Companion '+current+'.\n',encoding='utf-8')
        (output/'SHA256SUMS.txt').write_text(''.join(sha(f)+'  '+f.name+'\n' for f in sorted(output.iterdir()) if f.is_file()),encoding='ascii')
        return output,current
    except Exception:
        shutil.rmtree(output);raise


def upload_draft(directory,target_version):
    """Requires gh authenticated by publisher. Never publishes the draft automatically."""
    directory=Path(directory)
    if not shutil.which('gh'):raise ValueError('Instale GitHub CLI e execute gh auth login para enviar o rascunho, ou use o site do GitHub.')
    with (directory/'updates.json').open('rb') as f:payload=verify(f.read())
    if payload['version']!=target_version:raise ValueError('Versão do catálogo não corresponde à publicação.')
    cmd=['gh','release','create','v'+target_version,'--repo',REPOSITORY,'--draft','--title','AoE II Replay Companion '+target_version,'--notes-file',str(directory/'NOTAS_RELEASE.md')]
    # Do not upload source code, keys, build directories, replays or arbitrary files.
    files=[directory/'updates.json',directory/'SHA256SUMS.txt',*(directory/p['filename'] for p in payload['packages'])]
    for f in files:
        if not f.is_file():raise ValueError('Anexo ausente: '+f.name)
    subprocess.run(cmd+[str(f) for f in files],check=True)


def main():
    p=argparse.ArgumentParser(description='Prepara uma Release assinada; opcionalmente envia apenas um rascunho ao repositório público.')
    p.add_argument('--build',type=Path);p.add_argument('--base',type=Path);p.add_argument('--base-version');p.add_argument('--notes',type=Path)
    p.add_argument('--output',type=Path,default=ROOT/'publicacao_github');p.add_argument('--upload-draft',action='store_true');args=p.parse_args()
    build=args.build
    if build is None:
        info=json.loads((ROOT/'ultimo_build_patch.json').read_text(encoding='utf-8'));build=Path(info['dist'])
    notes=args.notes.read_text(encoding='utf-8') if args.notes else ''
    folder,v=prepare(build,args.output,args.base,args.base_version,notes)
    print('Publicação assinada preparada:',folder)
    if args.upload_draft:upload_draft(folder,v);print('Rascunho enviado. Revise e publique no GitHub quando os testes Windows passarem.')
    else:print('Nada foi enviado. Anexe updates.json e os .aoe2patch numa Release estável com tag v'+v+'.')
if __name__=='__main__':main()
