"""One-time publisher setup. Uses a project venv; never stores private keys in Git."""
from pathlib import Path
import os,subprocess,sys

def main():
    root=Path(__file__).resolve().parent
    if sys.version_info[:2]!=(3,12):raise RuntimeError('Use Python3.12: py -3.12 preparar_projeto.py')
    env=root/'.venv';python=env/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.is_file():subprocess.run([sys.executable,'-m','venv',str(env)],check=True)
    subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements.txt')],cwd=root,check=True)
    subprocess.run([str(python),'-m','tools.signing','init'],cwd=root,check=True)
    print('Projeto preparado. A chave privada está fora desta pasta. Versione somente companion_updates/trusted_keys.py.')
    print('Para compilar: py -3.12 gerar_instalador.py --somente-executavel')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
