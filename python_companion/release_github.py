"""Compatibility wrapper; use the project's environment, not global dependencies."""
from pathlib import Path
import subprocess,sys

def main():
    root=Path(__file__).resolve().parent
    python=root/'.venv/Scripts/python.exe'
    if not python.is_file():raise RuntimeError('Execute primeiro py -3.12 preparar_projeto.py.')
    subprocess.run([str(python),'-m','tools.publish_release',*sys.argv[1:]],cwd=root,check=True)
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
