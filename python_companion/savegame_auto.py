"""Descoberta local de perfis AoE2 DE. Sem leitura de memória do jogo."""
from pathlib import Path
import os
import time
import subprocess
import threading
import queue
import logging

EXTENSIONS = {'.aoe2record', '.aoe2spgame', '.aoe2mpgame'}


def roots():
    home = Path.home()
    bases = [home, home/'Documents', home/'OneDrive', home/'OneDrive/Documents']
    for key in ('USERPROFILE','OneDrive','OneDriveConsumer','OneDriveCommercial'):
        if os.environ.get(key):
            p = Path(os.environ[key]); bases.extend((p,p/'Documents'))
    if os.name == 'nt':
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders') as k:
                for name in ('Personal','{4C5C32FF-BB9D-43B0-BF86-3DFAE6D68CF3}'):
                    try:bases.append(Path(os.path.expandvars(winreg.QueryValueEx(k,name)[0])))
                    except OSError:pass
        except OSError:pass
    found = []
    for base in bases:
        for p in (base/'Games/Age of Empires 2 DE', base/'Age of Empires 2 DE'):
            if p not in found:found.append(p)
    return found


def running():
    if os.name != 'nt':return False
    try:
        r = subprocess.run(['tasklist','/FI','IMAGENAME eq AoE2DE_s.exe','/FO','CSV','/NH'],capture_output=True,timeout=5,creationflags=0x08000000)
        return b'aoe2de_s.exe' in r.stdout.lower()
    except (OSError,subprocess.TimeoutExpired):return None


def scan(search_roots=None):
    profiles = []
    for base in (roots() if search_roots is None else search_roots):
        try:children = list(Path(base).iterdir())
        except OSError:continue
        for profile in children:
            folder = profile/'savegame'
            if not folder.is_dir():continue
            files = {}
            try:
                for f in folder.iterdir():
                    if f.suffix.lower() not in EXTENSIONS:continue
                    try:
                        st = f.stat()
                        if f.is_file():files[str(f)] = (st.st_size,st.st_mtime_ns)
                    except OSError:pass
                # Prefer activity of game saves, not directory mtime changed by unrelated files.
                stamp = max((v[1] for v in files.values()),default=profile.stat().st_mtime_ns)
            except OSError:continue
            if not any(p['folder']==str(folder) for p in profiles):
                profiles.append({'folder':str(folder),'profile':profile.name,'files':files,'latest_ns':stamp})
    return profiles


def choose(profiles, previous=None, game_running=False, now_ns=None):
    if not profiles:return None
    previous = previous or {}
    now_ns = time.time_ns() if now_ns is None else now_ns
    def rank(p):
        changes = [v[1] for name,v in p['files'].items() if name in previous and v != previous[name] and v[1] >= now_ns-30_000_000_000]
        return (max(changes,default=0) if game_running else 0,p['latest_ns'],p['folder'])
    selected = max(profiles,key=rank)
    result = dict(selected)
    result['reason'] = 'gravação em atualização' if game_running and rank(selected)[0] else 'perfil com gravação mais recente'
    return result


def ativar(g):
    if g.get('_savegame_auto_0419'):return
    g['_savegame_auto_0419'] = True
    Base = g['Window']
    class Window(Base):
        def __init__(self,root,native):
            self._sg_manual = False
            self._sg_applying = False
            self._sg_force = True
            self._sg_events = queue.Queue()
            self._sg_stop = threading.Event()
            super().__init__(root,native)
            self._sg_manual = False
            threading.Thread(target=self._sg_worker,daemon=True).start()
            try:
                import tkinter as tk
                menu_name = root.cget('menu')
                menu = root.nametowidget(menu_name) if menu_name else tk.Menu(root,tearoff=False)
                if not menu_name:root.configure(menu=menu)
                menu.add_command(label='Detectar savegame automaticamente',command=self._sg_resume)
            except Exception:logging.exception('Menu de detecção automática')
            root.after(100,self._sg_poll)

        def _sg_resume(self):
            self._sg_manual = False
            self._sg_force = True
            self.status.set('Procurando perfil savegame automaticamente…')

        def _sg_worker(self):
            previous = {}
            while not self._sg_stop.is_set():
                try:
                    candidates = scan()
                    selected = choose(candidates,previous,running())
                    previous = {n:v for p in candidates for n,v in p['files'].items()}
                    self._sg_events.put(selected)
                except Exception:logging.exception('Detecção automática de savegame')
                self._sg_stop.wait(2)

        def _sg_poll(self):
            if getattr(self,'closing',False):self._sg_stop.set();return
            newest = None
            while not self._sg_events.empty():newest = self._sg_events.get_nowait()
            if newest and not self._sg_manual:
                current = str(self.folder.get())
                if self._sg_force or os.path.normcase(current) != os.path.normcase(newest['folder']):
                    self._sg_applying = True
                    try:
                        self._sg_force = False
                        self.folder.set(newest['folder'])
                        records = [(st[1],name) for name,st in newest['files'].items() if Path(name).suffix.lower()=='.aoe2record']
                        if records:self.attach(Path(max(records)[1]))
                        self.status.set('Savegame automático: '+newest['profile']+' · '+newest['reason'])
                        logging.info('Savegame automático: %s (%s)',newest['folder'],newest['reason'])
                    except Exception:logging.exception('Aplicar pasta savegame automática')
                    finally:self._sg_applying = False
            self.root.after(250,self._sg_poll)

        def choose_folder(self,*args,**kwargs):
            before = str(self.folder.get())
            result = super().choose_folder(*args,**kwargs)
            if str(self.folder.get()) != before:self._sg_manual = True
            return result

        def choose_file(self,*args,**kwargs):
            # An explicit replay selection must not be replaced by background detection.
            self._sg_manual = True
            return super().choose_file(*args,**kwargs)

        def close(self):
            self._sg_stop.set()
            return super().close()
    g['Window'] = Window


# PERFIL_SAVEGAME_PONTUAL_V1
_ativar_perfil_anterior = ativar
_roots_perfil_anterior = roots

def _perfil_config_path():
    return Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'AoE2Overlay' / 'perfil_savegame.json'

def _perfil_config():
    import json
    try:return json.loads(_perfil_config_path().read_text(encoding='utf-8'))
    except (OSError, ValueError):return {}

def _perfil_save(values):
    import json
    path = _perfil_config_path();path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(values,ensure_ascii=False),encoding='utf-8');temporary.replace(path)

def roots():
    result=list(_roots_perfil_anterior())
    for value in _perfil_config().get('search_roots',[]):
        path=Path(value)
        if path not in result:result.append(path)
    return result

def ativar(g):
    _ativar_perfil_anterior(g)
    if g.get('_perfil_savegame_pontual'):return
    g['_perfil_savegame_pontual']=True
    Base=g['Window']
    class Window(Base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            import tkinter as tk
            name=self.root.cget('menu');menu=self.root.nametowidget(name) if name else tk.Menu(self.root,tearoff=False)
            if not name:self.root.configure(menu=menu)
            menu.add_command(label='Selecionar perfil savegame…',command=self._perfil_manual)
            selected=_perfil_config().get('manual_folder')
            if selected and Path(selected).is_dir():self._perfil_apply(Path(selected))

        def _perfil_apply(self,folder):
            self._sg_manual=True
            self.folder.set(str(folder))
            try:
                records=list(folder.glob('*.aoe2record'))
                if records:self.attach(max(records,key=lambda p:p.stat().st_mtime_ns))
                self.status.set('Perfil manual: '+folder.parent.name+' | '+str(folder))
            except OSError as exc:self.status.set('Perfil selecionado; aguardando acesso à pasta: '+str(exc))

        def _perfil_manual(self):
            from tkinter import filedialog,messagebox
            value=filedialog.askdirectory(parent=self.root,title='Selecione a pasta savegame do perfil (qualquer unidade)',initialdir=self.folder.get() or str(Path.home()))
            if not value:return
            folder=Path(value)
            if folder.name.casefold()!='savegame' and (folder/'savegame').is_dir():folder=folder/'savegame'
            if folder.name.casefold()!='savegame':
                messagebox.showerror('Perfil','Selecione a pasta savegame ou a pasta do perfil que a contém.',parent=self.root);return
            config=_perfil_config();extra=config.get('search_roots',[])
            root=str(folder.parent.parent)
            if root not in extra:extra.append(root)
            config.update(manual_folder=str(folder),search_roots=extra)
            try:_perfil_save(config)
            except OSError as exc:
                messagebox.showerror('Perfil','Não foi possível salvar a seleção: '+str(exc),parent=self.root);return
            self._perfil_apply(folder)

        def _sg_resume(self):
            config=_perfil_config();config.pop('manual_folder',None)
            try:_perfil_save(config)
            except OSError:
                logging.exception('Não foi possível salvar o modo automático de perfil')
                self.status.set('Não foi possível salvar o modo automático.');return
            return super()._sg_resume()
    g['Window']=Window
