"""Inicialização isolada de Edge/Chrome e diagnóstico do renderizador PNG."""
from pathlib import Path
import ctypes,logging,os,shutil,subprocess,sys,threading
LOCK=threading.RLock()


def candidates(first=None):
    result=[]
    def add(path):
        if path and Path(path).is_file() and os.path.normcase(str(path)) not in {os.path.normcase(p) for p in result}:result.append(str(path))
    add(first)
    for key in ('PROGRAMFILES','PROGRAMFILES(X86)','LOCALAPPDATA'):
        if os.environ.get(key):
            for suffix in ('Microsoft/Edge/Application/msedge.exe','Google/Chrome/Application/chrome.exe'):
                add(Path(os.environ[key])/suffix)
    for name in ('msedge','chrome','chromium','chromium-browser','google-chrome'):add(shutil.which(name))
    return result


def clean_environment():
    env=os.environ.copy()
    if getattr(sys,'frozen',False):
        bundle=getattr(sys,'_MEIPASS',None)
        if bundle:
            base=Path(bundle).resolve()
            items=[]
            for item in env.get('PATH','').split(os.pathsep):
                try:inside=Path(item).resolve().is_relative_to(base)
                except (OSError,ValueError):inside=False
                if not inside:items.append(item)
            env['PATH']=os.pathsep.join(items)
        if sys.platform!='win32':
            original=env.get('LD_LIBRARY_PATH_ORIG')
            if original is None:env.pop('LD_LIBRARY_PATH',None)
            else:env['LD_LIBRARY_PATH']=original
    return env


def launch(command,stderr):
    env=clean_environment()
    # PyInstaller redirects DLL search to its bundle. External browsers need the
    # normal Windows DLL search. Restore the application's setting immediately.
    with LOCK:
        kernel=None;previous=None
        try:
            if sys.platform=='win32' and getattr(sys,'frozen',False):
                from ctypes import wintypes
                kernel=ctypes.WinDLL('kernel32',use_last_error=True)
                kernel.GetDllDirectoryW.argtypes=(wintypes.DWORD,wintypes.LPWSTR)
                kernel.GetDllDirectoryW.restype=wintypes.DWORD
                kernel.SetDllDirectoryW.argtypes=(wintypes.LPCWSTR,)
                kernel.SetDllDirectoryW.restype=wintypes.BOOL
                buffer=ctypes.create_unicode_buffer(32768)
                count=kernel.GetDllDirectoryW(len(buffer),buffer)
                if count>=len(buffer):raise OSError('Diretório de DLL excede o limite.')
                previous=buffer.value if count else None
                if not kernel.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
            return subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=stderr,env=env,
                                    creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        finally:
            if kernel is not None and not kernel.SetDllDirectoryW(previous):logging.error('Falha ao restaurar diretório de DLL do aplicativo.')


def report_failure(browser,process,stderr_path):
    try:
        with Path(stderr_path).open('rb') as f:
            f.seek(0,2);size=f.tell();f.seek(max(0,size-12000));tail=f.read().decode('utf-8',errors='replace')
    except OSError:tail='Não foi possível ler stderr do navegador.'
    code=process.returncode if process is not None else 'não iniciado'
    message='Navegador PNG: '+str(browser)+'\nCódigo de saída: '+str(code)+'\n'+tail
    logging.error('%s',message)
    try:
        directory=Path(os.environ.get('LOCALAPPDATA',Path.home()))/'AoE2Overlay';directory.mkdir(parents=True,exist_ok=True)
        (directory/'navegador_diagnostico.log').write_text(message,encoding='utf-8')
    except OSError:logging.exception('Falha ao salvar diagnóstico do navegador PNG')


def export_with_fallback(svg,png,find_browser,export_one):
    browsers=candidates(find_browser())
    if not browsers:raise RuntimeError('Edge/Chrome não encontrado. Instale um navegador compatível para gerar o minimapa.')
    failures=[]
    for browser in browsers:
        try:return export_one(svg,png,browser)
        except Exception as exc:
            logging.exception('Falha no renderizador com %s',browser)
            failures.append(Path(browser).name+': '+str(exc))
    raise RuntimeError('Falha ao gerar a imagem com os navegadores encontrados. Consulte aplicativo.log e navegador_diagnostico.log em %LOCALAPPDATA%\\AoE2Overlay. Último erro: '+failures[-1])
