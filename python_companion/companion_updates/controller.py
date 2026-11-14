"""Nonblocking startup check/download; all Tk operations remain on the UI thread."""
from pathlib import Path
import hashlib,logging,os,queue,shutil,subprocess,sys,threading,time,uuid
from patch_core import inventory,fingerprint
from . import transport
from .common import data_dir,install_dir,installed_version,read_json,settings,version,write_json
from .config import UPDATER
from .security import verify
from .processes import spawn

CHECK_INTERVAL=6*60*60


def choose_package(payload,root):
    current=installed_version(root)
    if current and version(payload['version'])<=version(current):return None
    actual=fingerprint(inventory(root))
    if any(p['target_fingerprint']==actual for p in payload['packages']):return None
    patches=[p for p in payload['packages'] if p['kind']=='patch' and p['base_fingerprint']==actual]
    if patches:return min(patches,key=lambda p:p['size'])
    return next((p for p in payload['packages'] if p['kind']=='full'),None)


class UpdateController:
    def __init__(self,window):
        self.window=window;self.root=window.root;self.install=install_dir()
        self.events=queue.Queue();self.busy=False;self.cancel=threading.Event();self.pending=None
        self.state='idle';self.message='Atualizações automáticas ativadas.';self.dialog_window=None
        self.status_var=None;self.check_button=None;self.download_button=None;self.install_button=None
        self.timer=self.root.after(200,self.poll)
        self.root.bind('<Destroy>',self.destroy,add='+')
        self.start_timer=self.root.after(1500,lambda:self.check(False))

    def destroy(self,event):
        if event.widget is not self.root:return
        self.cancel.set()
        for token in (self.timer,self.start_timer):
            try:self.root.after_cancel(token)
            except Exception:pass

    def notify(self,state,message):
        self.state=state;self.message=message
        if self.status_var is not None:self.status_var.set(message)
        if getattr(self,'banner_text',None) is not None:self.banner_text.set(message)
        if self.check_button is not None:self.check_button.configure(state='disabled' if self.busy else 'normal')
        if self.download_button is not None:self.download_button.configure(state='normal' if not self.busy and self.pending and self.state=='available' else 'disabled')
        if self.install_button is not None:self.install_button.configure(state='normal' if self.state=='ready' and not self.busy else 'disabled')

    def check(self,manual=False):
        if self.busy:return
        preferences=settings()
        if not manual and not preferences['auto_check']:return
        if not (self.install/'AoE2Overlay.exe').is_file():
            if manual:self.notify('idle','Execute a versão instalada para verificar atualizações deste computador.')
            return
        if manual:self.open_dialog()
        self.busy=True;self.notify('checking','Consultando atualizações…')
        def work():
            try:
                cache=data_dir()/'updates';cache.mkdir(parents=True,exist_ok=True)
                state=read_json(cache/'check.json',{})
                manifest_file=cache/'updates.json'
                # Cache is re-verified with the pinned key. A changed/new package is
                # fetched immediately on a manual check. Failed checks aren't cached.
                if not manual and manifest_file.is_file() and time.time()-state.get('checked_at',0)<CHECK_INTERVAL:
                    raw=manifest_file.read_bytes();payload=verify(raw)
                else:
                    raw=transport.fetch_manifest();payload=verify(raw)
                    temp=manifest_file.with_suffix('.tmp');temp.write_bytes(raw);temp.replace(manifest_file)
                    write_json(cache/'check.json',{'checked_at':time.time()})
                package=choose_package(payload,self.install)
                if package is None:self.events.put(('current',payload['version']));return
                directory=cache/payload['version'];directory.mkdir(parents=True,exist_ok=True)
                signed=directory/'updates.json';signed.write_bytes(raw)
                pending={'payload':payload,'package':package,'manifest':signed,'directory':directory}
                if preferences['auto_download']:
                    self.events.put(('status','Baixando atualização '+payload['version']+' em segundo plano…'))
                    path=transport.download(package,directory,self.progress,self.cancel)
                    pending['path']=path;self.events.put(('ready',pending))
                else:self.events.put(('available',pending))
            except Exception as exc:
                logging.info('Verificação de atualizações indisponível: %s',exc)
                self.events.put(('error',str(exc) if manual else 'Não foi possível consultar atualizações agora. O Companion continua disponível.'))
        threading.Thread(target=work,daemon=True).start()

    def progress(self,count,total):
        # One event per MiB at most, not one event per byte/frame.
        self.events.put(('status',f'Baixando atualização: {count*100//total}%'))

    def download_now(self):
        if self.busy or not self.pending:return
        self.busy=True;self.notify('downloading','Baixando atualização…');pending=dict(self.pending)
        def work():
            try:
                pending['path']=transport.download(pending['package'],pending['directory'],self.progress,self.cancel)
                self.events.put(('ready',pending))
            except Exception as exc:self.events.put(('error',str(exc)))
        threading.Thread(target=work,daemon=True).start()

    def show_banner(self):
        import tkinter as tk
        from tkinter import ttk
        if getattr(self,'banner',None) is not None:return
        self.banner=ttk.Frame(self.root,padding=(10,4))
        self.banner_text=tk.StringVar(master=self.root,value=self.message)
        ttk.Label(self.banner,textvariable=self.banner_text).pack(side='left',fill='x',expand=True)
        ttk.Button(self.banner,text='Atualizar',command=self.open_dialog).pack(side='right')
        packed=self.root.pack_slaves()
        options={'side':'bottom','fill':'x'}
        if packed:options['before']=packed[0]
        self.banner.pack(**options)

    def poll(self):
        if self.cancel.is_set():return
        while not self.events.empty():
            kind,value=self.events.get()
            if kind=='status':self.notify('downloading',value);continue
            self.busy=False
            if kind in ('ready','available'):
                self.pending=value
                if kind=='ready':
                    self.notify('ready','Atualização '+value['payload']['version']+' pronta para instalar.');self.show_banner()
                else:self.notify('available','Atualização '+value['payload']['version']+' disponível.');self.show_banner()
            elif kind=='current':self.pending=None;self.notify('current','Nenhuma atualização nova. Instalada: '+str(installed_version(self.install) or 'build identificado')+'; última publicada: '+value+'.')
            else:self.notify('error',value)
        self.timer=self.root.after(200,self.poll)

    def install_now(self):
        if self.busy or self.state!='ready' or not self.pending:return
        from tkinter import messagebox
        if not messagebox.askyesno('Reiniciar e atualizar','Fechar o Companion, instalar a atualização e reabrir automaticamente?',parent=self.dialog_window or self.root):return
        p=self.pending
        try:
            payload=verify(p['manifest'].read_bytes())
            package=next(x for x in payload['packages'] if x['filename']==p['package']['filename'])
            if transport.file_hash(p['path'])!=package['sha256']:raise ValueError('Arquivo baixado foi modificado; verifique novamente.')
            updater=self.install/UPDATER
            if not updater.is_file():raise ValueError('O aplicador integrado não está disponível nesta instalação.')
            directory=data_dir()/'updates/runner'/uuid.uuid4().hex;directory.mkdir(parents=True)
            runner=directory/UPDATER;shutil.copy2(updater,runner)
            spawn([str(runner),'--manifest',str(p['manifest']),'--package',str(p['path']),'--install',str(self.install),'--parent-pid',str(os.getpid())],cwd=directory)
        except Exception as exc:
            messagebox.showerror('Atualização',str(exc),parent=self.dialog_window or self.root);return
        self.window.close()

    def open_dialog(self):
        import tkinter as tk
        from tkinter import ttk
        if self.dialog_window is not None and self.dialog_window.winfo_exists():self.dialog_window.lift();return
        top=tk.Toplevel(self.root);self.dialog_window=top;top.title('Atualizações · AoE II Replay Companion');top.geometry('660x370')
        box=ttk.Frame(top,padding=18);box.pack(fill='both',expand=True)
        ttk.Label(box,text='Atualizações do Companion',font=('Segoe UI',16,'bold')).pack(anchor='w')
        ttk.Label(box,text='Instalada: '+str(installed_version(self.install) or 'build legado')).pack(anchor='w',pady=8)
        self.status_var=tk.StringVar(master=self.root,value=self.message)
        ttk.Label(box,textvariable=self.status_var,wraplength=610).pack(fill='x',pady=12)
        prefs=settings();check_var=tk.BooleanVar(master=top,value=prefs['auto_check']);download_var=tk.BooleanVar(master=top,value=prefs['auto_download'])
        def save_preferences():write_json(data_dir()/'update_settings.json',{'auto_check':check_var.get(),'auto_download':download_var.get()})
        ttk.Checkbutton(box,text='Verificar ao abrir o Companion',variable=check_var,command=save_preferences).pack(anchor='w')
        ttk.Checkbutton(box,text='Baixar atualizações automaticamente',variable=download_var,command=save_preferences).pack(anchor='w')
        row=ttk.Frame(box);row.pack(fill='x',pady=16)
        self.check_button=ttk.Button(row,text='Verificar agora',command=lambda:self.check(True));self.check_button.pack(side='left',padx=(0,8))
        self.download_button=ttk.Button(row,text='Baixar',command=self.download_now);self.download_button.pack(side='left',padx=(0,8))
        self.install_button=ttk.Button(row,text='Reiniciar e atualizar',command=self.install_now);self.install_button.pack(side='left')
        ttk.Label(box,text='O download é automático. A instalação acontece com o programa fechado, com backup e verificação da primeira abertura.',wraplength=610).pack(fill='x')
        def close():
            self.status_var=None;self.check_button=None;self.download_button=None;self.install_button=None;top.destroy()
        top.protocol('WM_DELETE_WINDOW',close)
        self.notify(self.state,self.message)


def ativar(g):
    if g.get('_automatic_updates_active'):return
    g['_automatic_updates_active']=True;Base=g['Window']
    class Window(Base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            import tkinter as tk
            self.update_controller=UpdateController(self)
            name=self.root.cget('menu');menu=self.root.nametowidget(name) if name else tk.Menu(self.root,tearoff=False)
            if not name:self.root.configure(menu=menu)
            menu.add_command(label='Atualizações…',command=self.update_controller.open_dialog)
    g['Window']=Window
