"""Build + signed packages. No version typing or manual file downloads for buyers."""
import subprocess,sys
from pathlib import Path

def main():
    root=Path(__file__).resolve().parent
    subprocess.run([sys.executable,str(root/'gerar_instalador.py'),'--somente-executavel'],cwd=root,check=True)
    python=root/'.venv/Scripts/python.exe'
    subprocess.run([str(python),'-m','tools.publish_release',*sys.argv[1:]],cwd=root,check=True)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
