from pathlib import Path
import argparse,json,subprocess,sys,shutil
from patch_core import create_patch,sha,inventory

def main():
    parser=argparse.ArgumentParser(description='Compila a versão nova e gera um patch de arquivos; não usa Inno Setup.')
    parser.add_argument('--base',type=Path,help='Pasta do build ou instalação da versão-base')
    parser.add_argument('--novo',type=Path,help='Pasta do novo build já compilado; pula a compilação')
    parser.add_argument('--sem-aplicador-exe',action='store_true',help='Distribuir aplicar_patch.py em vez de compilar o aplicador independente')
    args=parser.parse_args();root=Path(__file__).resolve().parent
    reference=root/'referencia_patch.json';last=json.loads(reference.read_text(encoding='utf-8')) if reference.exists() else {}
    base=args.base or (Path(last['dist']) if last.get('dist') else None)
    if base is None:
        import tkinter as tk
        from tkinter import filedialog
        ui=tk.Tk();ui.withdraw()
        path=filedialog.askdirectory(title='Selecione a instalação atual OU o build exato que foi instalado (pasta com AoE2Overlay.exe)')
        ui.destroy()
        if not path:raise ValueError('Nenhuma versão-base selecionada.')
        base=Path(path)
    inventory(base)
    default=last.get('version') if args.base is None else None
    if default is None and (base/'.patch_state.json').exists():default=json.loads((base/'.patch_state.json').read_text(encoding='utf-8')).get('version')
    old=input('Versão-base'+(' ['+default+']' if default else '')+': ').strip() or default
    version=input('Nova versão (exemplo 0.4.20): ').strip()
    if not old:raise ValueError('Informe a versão-base instalada.')
    import re
    if not all(re.fullmatch(r'\d+\.\d+\.\d+',v) for v in (old,version)):
        raise ValueError('Use três números nas versões, exemplo 0.4.20.')
    if tuple(map(int,version.split('.'))) <= tuple(map(int,old.split('.'))):
        raise ValueError('A nova versão deve ser superior à versão-base.')
    if args.novo:
        new=args.novo;builder=None
    else:
        marker=root/'ultimo_build_patch.json';marker.unlink(missing_ok=True)
        subprocess.run([sys.executable,str(root/'gerar_instalador.py'),'--somente-executavel'],cwd=root,check=True)
        if not marker.exists():raise ValueError('Execute primeiro py -3.12 ativar_patches.py.')
        result=json.loads(marker.read_text(encoding='utf-8'));new=Path(result['dist']);builder=result['python_build']
    output=root/'patches'/('AoE2Overlay-'+version+'.aoe2patch')
    if output.exists():raise ValueError('Já existe um patch com essa versão; escolha outra para preservar o pacote anterior.')
    manifest=create_patch(base,new,output,old,version)
    (output.with_suffix('.sha256')).write_text(sha(output)+'  '+output.name+'\n',encoding='ascii')
    print('Patch gerado:',output)
    print('Arquivos alterados:',len(manifest['changed']),'| Removidos:',len(manifest['removed']))
    print('Tamanho:',round(output.stat().st_size/1024/1024,2),'MB')
    if not args.sem_aplicador_exe:
        python=builder or sys.executable
        (root/'compilacoes/aplicador').mkdir(parents=True,exist_ok=True)
        subprocess.run([python,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed','--name','AtualizadorAoE2','--paths',str(root),'--distpath',str(root/'ferramentas_patch'),'--workpath',str(root/'compilacoes/aplicador/build'),'--specpath',str(root/'compilacoes/aplicador'),str(root/'aplicar_patch.py')],cwd=root,check=True)
        shutil.copy2(root/'ferramentas_patch/AtualizadorAoE2.exe',output.parent/'AtualizadorAoE2.exe')
        print('Aplicador independente:',output.parent/'AtualizadorAoE2.exe')
    reference.write_text(json.dumps({'dist':str(new.resolve()),'version':version},indent=2),encoding='utf-8')
    print('Distribua o patch e AtualizadorAoE2.exe. O destinatário não precisa de Python.')
    print('Guarde o build gerado: ele será a base do próximo patch. Gere patches diferentes para versões-base diferentes.')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
