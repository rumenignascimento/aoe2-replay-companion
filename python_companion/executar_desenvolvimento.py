from pathlib import Path
import os,subprocess

def main():
    root=Path(__file__).resolve().parent
    python=root/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not python.is_file():raise RuntimeError('Execute preparar_projeto.py antes de abrir o código em desenvolvimento.')
    subprocess.run([str(python),str(root/'painel_jogadores.py')],cwd=root,check=True)
if __name__=='__main__':main()
