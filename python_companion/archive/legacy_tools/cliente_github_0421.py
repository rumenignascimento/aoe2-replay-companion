"""Atualizações públicas pelo GitHub Releases, sem token embutido no aplicativo."""
from pathlib import Path
import hashlib,json,os,queue,re,subprocess,sys,threading,urllib.request,urllib.error
from urllib.parse import urlsplit
from patch_core import inventory,fingerprint,sha

REPOSITORY='rumenignascimento/aoe2-companion-updates'


def version(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):raise ValueError('Versão inválida na publicação.')
    return tuple(map(int,value.split('.')))


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'AoE2-Replay-Companion-Updater','Accept':'application/vnd.github+json'}),timeout=30)


def read_json(url,limit=256*1024):
    with request(url) as response:
        raw=response.read(limit+1)
    if len(raw)>limit:raise ValueError('Resposta de atualização excessivamente grande.')
    return json.loads(raw.decode('utf-8'))


def validate(data,repo):
    if data.get('schema')!=1 or data.get('app')!='AoE2Overlay' or data.get('repository')!=repo:raise ValueError('Metadados de atualização incompatíveis.')
    if version(data['version'])<=version(data['base_version']):raise ValueError('Sequência de versões inválida.')
    for key in ('base_fingerprint','target_fingerprint'):
        if not re.fullmatch(r'[a-f0-9]{64}',data.get(key,'')):raise ValueError('Identificação de build inválida.')
    prefix='https://github.com/'+repo+'/releases/download/v'+data['version']+'/'
    for key in ('patch','updater'):
        a=data[key];name=a['filename']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',name) or a['url']!=prefix+name:raise ValueError('Endereço de download fora da publicação esperada.')
        if key=='patch' and name!='AoE2Overlay-'+data['version']+'.aoe2patch':raise ValueError('Nome de patch inválido.')
        if key=='updater' and name!='AtualizadorAoE2.exe':raise ValueError('Nome de aplicador inválido.')
        if not re.fullmatch(r'[a-f0-9]{64}',a.get('sha256','')):raise ValueError('Hash de download inválido.')
        if type(a.get('size')) is not int or not 0<a['size']<=2*1024**3:raise ValueError('Tamanho de arquivo inválido.')
    return data


def find_update(repo,current):
    releases=read_json('https://api.github.com/repos/'+repo+'/releases?per_page=30',2*1024*1024)
    if not isinstance(releases,list):raise ValueError('Resposta inesperada do GitHub.')
    stable=[]
    for r in releases:
        tag=r.get('tag_name','')
        if r.get('draft') or r.get('prerelease') or not re.fullmatch(r'v\d+\.\d+\.\d+',tag):continue
        stable.append(r)
    stable.sort(key=lambda r:version(r['tag_name'][1:]),reverse=True)
    seen=False;latest=None
    for r in stable:
        asset=next((a for a in r.get('assets',[]) if a.get('name')=='atualizacao.json'),None)
        if not asset:continue
        url='https://github.com/'+repo+'/releases/download/'+r['tag_name']+'/atualizacao.json'
        if asset.get('browser_download_url')!=url:raise ValueError('Metadados fora do repositório configurado.')
        data=validate(read_json(url),repo)
        if data['version']!=r['tag_name'][1:]:raise ValueError('Tag e versão da publicação não correspondem.')
        if latest is None:latest=data['version']
        seen=True
        if data['target_fingerprint']==current:
            if data['version']==latest:return {'status':'current','version':latest}
        if data['base_fingerprint']==current:
            return {'status':'available','update':data,'latest':latest}
    return {'status':'incompatible' if seen else 'empty','latest':latest}


def download(asset,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    target=directory/asset['filename'];temp=target.with_suffix(target.suffix+'.download')
    try:
        h=hashlib.sha256();count=0
        with request(asset['url']) as response,temp.open('wb') as out:
            final=urlsplit(response.geturl())
            if final.scheme!='https' or not (final.hostname=='github.com' or (final.hostname or '').endswith('.githubusercontent.com')):raise ValueError('Redirecionamento de download inesperado.')
            for chunk in iter(lambda:response.read(1024*1024),b''):
                count+=len(chunk)
                if count>asset['size']:raise ValueError('Download excede o tamanho anunciado.')
                h.update(chunk);out.write(chunk)
        if count!=asset['size'] or h.hexdigest()!=asset['sha256']:raise ValueError('A integridade do download não confere.')
        os.replace(temp,target);return target
    finally:temp.unlink(missing_ok=True)


def dialog(window):
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    existing=getattr(window,'_updates_dialog_0421',None)
    if existing is not None and existing.winfo_exists():existing.lift();return
    top=tk.Toplevel(window.root);window._updates_dialog_0421=top
    top.title('Atualizações · AoE II Replay Companion');top.geometry('650x340')
    box=ttk.Frame(top,padding=18);box.pack(fill='both',expand=True)
    ttk.Label(box,text='Atualizações do Companion',font=('Segoe UI',16,'bold')).pack(anchor='w',pady=(0,12))
    ttk.Label(box,text='Canal público: '+REPOSITORY,wraplength=600).pack(anchor='w')
    status=tk.StringVar(master=top,value='Clique em Verificar. Não é necessário entrar no GitHub.')
    ttk.Label(box,textvariable=status,wraplength=600).pack(anchor='w',pady=14)
    install=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Programs/AoE2Overlay'
    selected=[install];data=[None];downloads=[None];events=queue.Queue();busy=[False]
    def task(fn):
        busy[0]=True;check.config(state='disabled');get.config(state='disabled');apply.config(state='disabled')
        def worker():
            try:events.put(('ok',fn()))
            except urllib.error.HTTPError as e:events.put(('error','O repositório público ou a Release ainda não está disponível.' if e.code==404 else 'O GitHub recusou a consulta (HTTP '+str(e.code)+'). Tente novamente mais tarde.'))
            except Exception as e:events.put(('error',str(e)))
        threading.Thread(target=worker,daemon=True).start()
    def check_now():
        if busy[0]:return
        if not (selected[0]/'AoE2Overlay.exe').is_file():
            p=filedialog.askdirectory(parent=top,title='Selecione a instalação do Companion, com AoE2Overlay.exe')
            if not p:return
            selected[0]=Path(p)
        data[0]=None;downloads[0]=None;status.set('Identificando o build instalado e consultando o GitHub…')
        def work():return ('check',find_update(REPOSITORY,fingerprint(inventory(selected[0]))))
        task(work)
    def get_now():
        update=data[0]
        if busy[0] or update is None:return
        status.set('Baixando o patch e o aplicador. Aguarde a conferência de integridade…')
        destination=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AoE2Overlay/atualizacoes'/update['version']
        def work():return ('download',(download(update['patch'],destination),download(update['updater'],destination)))
        task(work)
    def install_now():
        if busy[0] or downloads[0] is None:return
        if not messagebox.askyesno('Aplicar atualização','Fechar o Companion e abrir o aplicador? No aplicador, clique em Aplicar patch.',parent=top):return
        patch,updater=downloads[0]
        try:
            for key,path in [('patch',patch),('updater',updater)]:
                if sha(path)!=data[0][key]['sha256']:raise ValueError('O arquivo baixado foi modificado; baixe novamente.')
            subprocess.Popen([str(updater),'--instalacao',str(selected[0]),'--patch',str(patch)],cwd=updater.parent)
        except Exception as e:messagebox.showerror('Atualização',str(e),parent=top);return
        window.close()
    row=ttk.Frame(box);row.pack(fill='x',pady=12)
    check=ttk.Button(row,text='Verificar',command=check_now);check.pack(side='left',padx=(0,8))
    get=ttk.Button(row,text='Baixar atualização',command=get_now,state='disabled');get.pack(side='left',padx=(0,8))
    apply=ttk.Button(row,text='Fechar e abrir aplicador',command=install_now,state='disabled');apply.pack(side='left')
    ttk.Label(box,text='O patch só é oferecido quando corresponde ao build instalado. Configurações e backups são preservados.',wraplength=600).pack(anchor='w',pady=10)
    poll_id=[None]
    def poll():
        if not top.winfo_exists():return
        if not events.empty():
            kind,value=events.get();busy[0]=False;check.config(state='normal')
            if kind=='error':status.set(value)
            elif value[0]=='download':
                downloads[0]=value[1];status.set('Downloads conferidos. Clique em Fechar e abrir aplicador.');apply.config(state='normal')
            else:
                result=value[1]
                if result['status']=='available':
                    data[0]=result['update'];get.config(state='normal');status.set('Atualização disponível: '+data[0]['base_version']+' → '+data[0]['version']+'. Última publicada: '+result['latest']+'.')
                elif result['status']=='current':status.set('Você está na versão mais recente publicada: '+result['version']+'.')
                elif result['status']=='empty':status.set('Ainda não há uma Release estável com atualizacao.json neste repositório.')
                else:status.set('Não há patch compatível com este build nas 30 Releases mais recentes. Consulte o publicador para obter o patch correto ou um instalador completo.')
        poll_id[0]=top.after(150,poll)
    def closing():
        if busy[0]:messagebox.showinfo('Atualização','Aguarde a operação terminar.',parent=top)
        else:top.destroy()
    def cleanup(event):
        if event.widget is top and poll_id[0] is not None:
            try:top.after_cancel(poll_id[0])
            except tk.TclError:pass
    top.bind('<Destroy>',cleanup,add='+')
    top.protocol('WM_DELETE_WINDOW',closing);poll()


def ativar(g):
    if g.get('_github_updates_0421'):return
    g['_github_updates_0421']=True;Base=g['Window']
    class Window(Base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            import tkinter as tk
            name=self.root.cget('menu');menu=self.root.nametowidget(name) if name else tk.Menu(self.root,tearoff=False)
            if not name:self.root.configure(menu=menu)
            menu.add_command(label='Verificar atualizações…',command=lambda:dialog(self))
    g['Window']=Window
