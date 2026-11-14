"""Independent process: verify signed artifacts, update, restart and check startup."""
from pathlib import Path
import argparse,ctypes,json,logging,os,queue,subprocess,threading,time,uuid
from patch_core import apply_patch,rollback,sha
from .common import data_dir,installed_version,read_json,version
from .health import marker
from .security import verify
from .config import EXECUTABLE
from .processes import spawn


def wait_parent(pid,timeout=60):
    if not pid:return
    if type(pid) is not int or pid<=0 or pid==os.getpid():raise ValueError('Processo de origem inválido.')
    if os.name=='nt':
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD);kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.WaitForSingleObject.argtypes=(wintypes.HANDLE,wintypes.DWORD);kernel.WaitForSingleObject.restype=wintypes.DWORD
        kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
        handle=kernel.OpenProcess(0x00100000,False,pid)
        if not handle:return
        try:
            result=kernel.WaitForSingleObject(handle,int(timeout*1000))
            if result!=0:raise TimeoutError('O Companion ainda não fechou. Feche-o e tente novamente.')
        finally:kernel.CloseHandle(handle)
    else:
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            try:os.kill(pid,0)
            except ProcessLookupError:return
            time.sleep(.1)
        raise TimeoutError('O aplicativo ainda não fechou.')


def apply_signed(manifest_file,package_file,root,parent_pid=None,health_timeout=45,progress=None):
    root=Path(root).resolve();package_file=Path(package_file)
    payload=verify(Path(manifest_file).read_bytes())
    package=next((p for p in payload['packages'] if p['filename']==package_file.name),None)
    if package is None or package_file.stat().st_size!=package['size'] or sha(package_file)!=package['sha256']:
        raise ValueError('Pacote não corresponde à publicação assinada.')
    current=installed_version(root)
    if current is not None and version(payload['version'])<=version(current):raise ValueError('A versão instalada já é igual ou superior.')
    import zipfile
    with zipfile.ZipFile(package_file) as z:
        if z.getinfo('manifest.json').file_size>10*1024**2:raise ValueError('Manifesto excessivo.')
        m=json.loads(z.read('manifest.json'))
    if m.get('target_fingerprint')!=package['target_fingerprint'] or m.get('version')!=package['version']:
        raise ValueError('A definição do build não corresponde à assinatura.')
    if (m.get('format')==1)!=(package['kind']=='patch'):raise ValueError('Tipo do pacote não corresponde à assinatura.')
    if package['kind']=='patch' and m.get('base_fingerprint')!=package['base_fingerprint']:raise ValueError('A base não corresponde à assinatura.')
    if progress:progress('Aguardando o Companion fechar…')
    wait_parent(parent_pid)
    if progress:progress('Aplicando atualização com backup…')
    result=apply_patch(package_file,root)
    token=uuid.uuid4().hex;health=marker(token);child=None
    try:
        if progress:progress('Atualização aplicada. Verificando a primeira abertura…')
        child=spawn([str(root/EXECUTABLE)],cwd=root,extra_env={'AOE2_COMPANION_UPDATE_TOKEN':token})
        end=time.monotonic()+health_timeout
        while time.monotonic()<end:
            info=read_json(health,{})
            if info.get('token')==token and info.get('version')==payload['version'] and info.get('started') is True:
                return result
            if child.poll() is not None:raise RuntimeError('A nova versão encerrou antes de confirmar a abertura.')
            time.sleep(.2)
        raise TimeoutError('A nova versão não confirmou a abertura no prazo.')
    except Exception:
        if child is not None and child.poll() is None:
            child.terminate();child.wait(timeout=10)
        rollback(root)
        # Launch the restored version normally; never declare the failed version healthy.
        try:spawn([str(root/EXECUTABLE)],cwd=root)
        except OSError:logging.exception('Não foi possível abrir a versão restaurada')
        raise RuntimeError('A nova versão não iniciou corretamente. A versão anterior foi restaurada; consulte aplicativo.log.')
    finally:health.unlink(missing_ok=True)


def main():
    import tkinter as tk
    from tkinter import ttk,messagebox
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',required=True);parser.add_argument('--package',required=True)
    parser.add_argument('--install',required=True);parser.add_argument('--parent-pid',type=int);args=parser.parse_args()
    directory=data_dir();directory.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(filename=directory/'updater.log',level=logging.INFO,encoding='utf-8')
    root=tk.Tk();root.title('Atualização · AoE II Replay Companion');root.geometry('620x180')
    status=tk.StringVar(value='Preparando atualização…');ttk.Label(root,textvariable=status,wraplength=570,padding=20).pack(fill='both',expand=True)
    events=queue.Queue();finished=[False]
    def work():
        try:
            result=apply_signed(args.manifest,args.package,args.install,args.parent_pid,progress=lambda s:events.put(('status',s)))
            events.put(('ok','Atualizado para '+result['version']+'. O Companion foi reaberto.'))
        except Exception as e:logging.exception('Falha na atualização');events.put(('error',str(e)))
    def poll():
        while not events.empty():
            kind,value=events.get();status.set(value)
            if kind in ('ok','error'):
                finished[0]=True
                (messagebox.showinfo if kind=='ok' else messagebox.showerror)('Atualização',value,parent=root)
                root.destroy();return
        root.after(100,poll)
    root.protocol('WM_DELETE_WINDOW',lambda:root.destroy() if finished[0] else messagebox.showinfo('Atualização','Aguarde o término da atualização.',parent=root))
    threading.Thread(target=work,daemon=True).start();poll();root.mainloop()
