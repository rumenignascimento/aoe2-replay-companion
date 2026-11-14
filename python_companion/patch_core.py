"""Patches de arquivos para builds PyInstaller onedir do AoE2Overlay."""
from pathlib import Path, PurePosixPath
import hashlib,json,os,shutil,tempfile,time,zipfile,uuid

APP='AoE2Overlay'
RESERVED={'.patch_state.json','.patch_transaction.json','.patch_lock'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def safe_name(name):
    if not isinstance(name,str) or not name or '\\' in name or ':' in name:raise ValueError('Caminho inválido no patch.')
    p=PurePosixPath(name)
    if p.is_absolute() or any(x in ('','.', '..') for x in name.split('/')):raise ValueError('Caminho fora da instalação.')
    if any(x.rstrip(' .')!=x for x in p.parts):raise ValueError('Nome incompatível com Windows.')
    if p.parts[0].lower() in {'.patch_backups',*RESERVED}:raise ValueError('Caminho reservado.')
    for part in p.parts:
        stem=part.split('.')[0].upper()
        if stem in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
            raise ValueError('Nome reservado do Windows.')
    return name

def inventory(folder):
    folder=Path(folder)
    if not (folder/'AoE2Overlay.exe').is_file():raise ValueError('Selecione a pasta que contém AoE2Overlay.exe.')
    files={}
    info=folder/'build-info.json'
    if info.is_file():
        metadata=json.loads(info.read_text(encoding='utf-8'))
        managed=metadata.get('managed_files')
        if not isinstance(managed,list) or not 1<=len(managed)<=20000 or 'build-info.json' not in managed:
            raise ValueError('Inventário do build inválido.')
        for name in managed:
            safe_name(name);p=target_path(folder.resolve(),name)
            if not p.is_file():raise ValueError('Arquivo do build ausente: '+name)
            files[name]=sha(p)
        check_map(files);return files
    for p in sorted(folder.rglob('*')):
        if p.is_symlink():raise ValueError('Links simbólicos não são aceitos no build.')
        rel=p.relative_to(folder).as_posix()
        if rel.split('/')[0] in RESERVED|{'.patch_backups'} or rel.lower().startswith('unins'):continue
        if p.is_file():files[safe_name(rel)]=sha(p)
    check_map(files)
    return files

def check_map(files):
    if not isinstance(files,dict) or not files:raise ValueError('Inventário vazio ou inválido.')
    seen=set()
    for n,h in files.items():
        safe_name(n)
        if n.casefold() in seen:raise ValueError('Nomes duplicados no Windows.')
        seen.add(n.casefold())
        if not isinstance(h,str) or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):raise ValueError('Hash inválido.')
    if 'AoE2Overlay.exe' not in files:raise ValueError('Build sem executável.')
    lowered={n.casefold() for n in files}
    for name in lowered:
        if any('/'.join(name.split('/')[:i]) in lowered for i in range(1,len(name.split('/')))):
            raise ValueError('Colisão entre arquivo e diretório.')

def fingerprint(files):return hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def create_patch(base,new,output,old_version,new_version):
    def version(s):
        parts=s.split('.')
        if len(parts)!=3 or not all(x.isdigit() for x in parts):raise ValueError('Versão deve ter três números.')
        return tuple(map(int,parts))
    if version(new_version)<=version(old_version):raise ValueError('A versão nova deve ser superior à versão-base.')
    old=inventory(base);current=inventory(new)
    changed=[n for n,h in current.items() if old.get(n)!=h]
    removed=sorted(set(old)-set(current))
    if not changed and not removed:raise ValueError('Os dois builds são iguais; não há patch a gerar.')
    m={'format':1,'app':APP,'base_version':old_version,'version':new_version,'base':old,'target':current,'changed':changed,'removed':removed,'base_fingerprint':fingerprint(old),'target_fingerprint':fingerprint(current)}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('manifest.json',json.dumps(m,ensure_ascii=False,indent=2))
        for n in changed:z.write(Path(new)/n,'payload/'+n)
    return m

def target_path(root,name):
    safe_name(name);p=root/name
    for part in [p,*p.parents]:
        if part==root.parent:break
        if part.is_symlink():raise ValueError('Link simbólico na instalação: '+name)
    if not p.resolve().is_relative_to(root.resolve()):raise ValueError('Caminho fora da instalação.')
    return p

def atomic_json(path,data):
    temp=path.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(temp,path)

def restore(root,journal):
    """Restaura somente arquivos envolvidos na transação, com hashes de backup."""
    root=Path(root).resolve()
    ident=journal['id']
    if not isinstance(ident,str) or len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Backup inválido.')
    backup=root/'.patch_backups'/ident
    if (root/'.patch_backups').is_symlink() or backup.is_symlink():raise ValueError('Link no diretório de backup.')
    for n,h in journal['before'].items():
        target=target_path(root,n)
        if h is not None:
            saved=backup/'files'/n
            if saved.is_symlink() or not saved.is_file() or sha(saved)!=h:raise ValueError('Backup inválido: '+n)
    for n,h in journal['before'].items():
        target=target_path(root,n)
        if h is not None:
            if target.is_file() and sha(target)==h:continue
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup/'files'/n,target)
        else:target.unlink(missing_ok=True)
    state=journal.get('previous_state')
    if state is None:(root/'.patch_state.json').unlink(missing_ok=True)
    else:atomic_json(root/'.patch_state.json',state)
    (root/'.patch_transaction.json').unlink(missing_ok=True)

def apply_patch(archive,root):
    root=Path(root).resolve()
    if not (root/'AoE2Overlay.exe').is_file():raise ValueError('Pasta de instalação inválida.')
    lock=root/'.patch_lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise ValueError('Há outra atualização em curso, ou um bloqueio de execução interrompida. Feche os aplicadores antes de remover .patch_lock.') from None
    os.close(fd)
    try:return _apply(archive,root)
    finally:lock.unlink(missing_ok=True)

def _apply(archive,root):
    journal_path=root/'.patch_transaction.json'
    if journal_path.exists():
        restore(root,json.loads(journal_path.read_text(encoding='utf-8')))
    with tempfile.TemporaryDirectory(prefix='aoe2patch-') as stage_name:
        stage=Path(stage_name)
        with zipfile.ZipFile(archive) as z:
            names=z.namelist()
            if len(names)!=len(set(names)) or sum(i.file_size for i in z.infolist())>2*1024**3:raise ValueError('Pacote duplicado ou excessivamente grande.')
            if z.getinfo('manifest.json').file_size>10*1024**2:raise ValueError('Manifesto excessivamente grande.')
            m=json.loads(z.read('manifest.json'))
            if m.get('format') not in (1,2) or m.get('app')!=APP:raise ValueError('Pacote incompatível.')
            new=m['target'];check_map(new)
            if fingerprint(new)!=m['target_fingerprint']:raise ValueError('Manifesto corrompido.')
            if m['format']==2:
                current=inventory(root)
                old={n:h for n,h in current.items() if n in new or (root/'build-info.json').is_file()}
                m['base_version']=json.loads((root/'build-info.json').read_text(encoding='utf-8')).get('version','unknown') if (root/'build-info.json').exists() else 'legacy'
            else:
                old=m['base'];check_map(old)
                if fingerprint(old)!=m['base_fingerprint']:raise ValueError('Base corrompida.')
            changed=sorted(n for n,h in new.items() if old.get(n)!=h);removed=sorted(set(old)-set(new))
            if m['format']==1 and (sorted(m['changed'])!=changed or sorted(m['removed'])!=removed):raise ValueError('Lista de alterações inválida.')
            payload_names=list(new) if m['format']==2 else changed
            if set(names)!={'manifest.json',*('payload/'+n for n in payload_names)}:raise ValueError('Conteúdo inesperado no ZIP.')
            total=sum(i.file_size for i in z.infolist())
            if shutil.disk_usage(root).free<total*2+10*1024**2:raise OSError('Espaço insuficiente para estágio e backup.')
            for n,h in old.items():
                p=target_path(root,n)
                if not p.is_file() or sha(p)!=h:raise ValueError('A instalação não corresponde à versão-base deste patch: '+n)
            for n in payload_names:
                target=target_path(root,n)
                if n not in old and target.exists():raise ValueError('O novo arquivo já existe na instalação: '+n)
                dest=stage/n;dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open('payload/'+n) as src,dest.open('wb') as out:shutil.copyfileobj(src,out)
                if sha(dest)!=new[n]:raise ValueError('Arquivo do patch corrompido: '+n)
        ident=uuid.uuid4().hex;backup=root/'.patch_backups'/ident
        if (root/'.patch_backups').is_symlink():raise ValueError('Link no diretório de backup.')
        backup.mkdir(parents=True)
        if backup.is_symlink():raise ValueError('Pasta de backup inválida.')
        previous_state=json.loads((root/'.patch_state.json').read_text(encoding='utf-8')) if (root/'.patch_state.json').exists() else None
        journal={'id':ident,'before':{n:old.get(n) for n in changed+removed},'previous_state':previous_state,'version':m['version'],'base_version':m['base_version']}
        for n,h in journal['before'].items():
            if h is not None:
                dest=backup/'files'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/n,dest)
        atomic_json(backup/'journal.json',journal)
        atomic_json(journal_path,journal)
        try:
            for n in removed:(root/n).unlink()
            for n in changed:
                dest=root/n;dest.parent.mkdir(parents=True,exist_ok=True)
                temp=backup/'pending'/n;temp.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stage/n,temp);os.replace(temp,dest)
            for n,h in new.items():
                if sha(root/n)!=h:raise ValueError('Verificação final falhou: '+n)
            atomic_json(root/'.patch_state.json',{'version':m['version'],'fingerprint':fingerprint(new),'last_backup':ident})
            journal_path.unlink()
        except Exception:
            restore(root,journal)
            raise
        return m

def _rollback(root):
    root=Path(root).resolve()
    state=json.loads((root/'.patch_state.json').read_text(encoding='utf-8'))
    ident=state['last_backup']
    if len(ident)!=32 or any(c not in '0123456789abcdef' for c in ident):raise ValueError('Backup inválido.')
    journal=json.loads((root/'.patch_backups'/ident/'journal.json').read_text(encoding='utf-8'))
    restore(root,journal)
    return journal


def rollback(root):
    root=Path(root).resolve();lock=root/'.patch_lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:raise ValueError('Há outra atualização em curso ou um bloqueio de execução interrompida.') from None
    os.close(fd)
    try:return _rollback(root)
    finally:lock.unlink(missing_ok=True)
