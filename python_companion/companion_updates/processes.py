"""Spawn an independent frozen application without inheriting its parent bundle."""
import ctypes,logging,os,subprocess,sys,threading
from pathlib import Path
_LOCK=threading.RLock()


def spawn(command,cwd=None,extra_env=None):
    env=os.environ.copy();env['PYINSTALLER_RESET_ENVIRONMENT']='1'
    env.pop('AOE2_COMPANION_UPDATE_TOKEN',None)
    if extra_env:env.update(extra_env)
    bundle=getattr(sys,'_MEIPASS',None)
    if bundle:
        entries=[]
        for entry in env.get('PATH','').split(os.pathsep):
            try:inside=Path(entry).resolve().is_relative_to(Path(bundle).resolve())
            except (OSError,ValueError):inside=False
            if not inside:entries.append(entry)
        env['PATH']=os.pathsep.join(entries)
    with _LOCK:
        kernel=None;old=None
        try:
            if sys.platform=='win32' and getattr(sys,'frozen',False):
                from ctypes import wintypes
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.GetDllDirectoryW.argtypes=(wintypes.DWORD,wintypes.LPWSTR);kernel.GetDllDirectoryW.restype=wintypes.DWORD
                kernel.SetDllDirectoryW.argtypes=(wintypes.LPCWSTR,);kernel.SetDllDirectoryW.restype=wintypes.BOOL
                buffer=ctypes.create_unicode_buffer(32768);count=kernel.GetDllDirectoryW(len(buffer),buffer)
                if count>=len(buffer):raise OSError('Diretório de DLL inválido.')
                old=buffer.value if count else None
                if not kernel.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
            return subprocess.Popen(command,cwd=cwd,env=env)
        finally:
            if kernel is not None and not kernel.SetDllDirectoryW(old):logging.error('Não foi possível restaurar o diretório de DLL.')
