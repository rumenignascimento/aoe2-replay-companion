import ast
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import textwrap
from datetime import datetime

def executar(*comando):
    subprocess.run([str(item) for item in comando], check=True)

def gravar(caminho, conteudo):
    caminho.write_text(textwrap.dedent(conteudo).lstrip(), encoding='utf-8')

def main():
    somente_executavel_patch = '--somente-executavel' in sys.argv
    if sys.platform != 'win32':
        raise RuntimeError('Execute este script no Windows.')
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError('Use Python 3.12: py -3.12 gerar_instalador.py')
    if struct.calcsize('P') != 8:
        raise RuntimeError('Use Python 3.12 de 64 bits.')
    projeto = Path(__file__).resolve().parent
    arquivos = ['gerador_mapa.py', 'mapa_overlay.py', 'overlay_legendas.py', 'minimapa_aoe2.py', 'painel_aoe2.py', 'painel_tropas.py', 'painel_melhorado.py', 'painel_jogadores.py', 'rotas_012.py', 'painel_movel.py', 'central_replay.py', 'ajuda_replay.py', 'gaia_minimapa.py', 'recursos_manuais.py', 'painel_horizontal.py', 'filtros_construcoes.py', 'controles_camadas.py', 'acabamento_visual.py', 'captura_atalhos.py', 'idiomas_app.py', 'catalogo_idiomas.py', 'unidades_034.py', 'unidades_assets_034.py', 'enquadramento_035.py', 'painel_tabela_036.py', 'abas_clicaveis_040.py', 'savegame_auto.py', 'layout_0420.py', 'cliente_github_0421.py', 'patch_core.py', 'navegador_png_0422.py']
    faltantes = [nome for nome in arquivos if not (projeto / nome).is_file()]
    if not (projeto / 'icones_aoe2').is_dir():
        faltantes.append('pasta icones_aoe2')
    if faltantes:
        raise RuntimeError('Coloque este script na pasta completa do projeto.\nNão encontrei:\n' + '\n'.join(faltantes))
    candidatos = [Path(os.environ.get(variavel, '')) / 'Inno Setup 6' / 'ISCC.exe' for variavel in ('ProgramFiles(x86)', 'ProgramFiles')]
    candidatos.append(Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs' / 'Inno Setup 6' / 'ISCC.exe')
    encontrado = shutil.which('ISCC.exe')
    if encontrado:
        candidatos.append(Path(encontrado))
    compilador = next((p for p in candidatos if p.is_file()), None)
    if compilador is None and (not somente_executavel_patch):
        raise RuntimeError('Instale Inno Setup 6:\nhttps://jrsoftware.org/isdl.php')
    momento = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    trabalho = projeto / 'compilacoes' / momento
    fonte = trabalho / 'src'
    fonte.mkdir(parents=True)
    print('\nPreparando cópia do projeto...')
    for nome in arquivos:
        texto = (projeto / nome).read_text(encoding='utf-8-sig')
        texto = texto.replace('Path(__file__).resolve().with_name("configuracoes_aoe2.json")', '(DATA_DIR / "configuracoes_aoe2.json")')
        texto = texto.replace('Path(__file__).resolve().parent', 'DATA_DIR')
        arvore = ast.parse(texto)
        linhas = texto.splitlines(keepends=True)
        inserir = 0
        for indice, item in enumerate(arvore.body):
            if indice == 0 and isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                inserir = item.end_lineno
            elif isinstance(item, ast.ImportFrom) and item.module == '__future__':
                inserir = item.end_lineno
            else:
                break
        linhas.insert(inserir, '\nfrom caminhos_app import DATA_DIR\n')
        texto = ''.join(linhas)
        ast.parse(texto)
        (fonte / nome).write_text(texto, encoding='utf-8')
    shutil.copytree(projeto / 'icones_aoe2', fonte / 'icones_aoe2')
    shutil.copy2(projeto / 'icone.ico', fonte / 'icone.ico')
    gravar(fonte / 'caminhos_app.py', '\n        import os\n        import shutil\n        import sys\n        from pathlib import Path\n\n        BUNDLE_DIR = Path(\n            getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)\n        )\n        DATA_DIR = (\n            Path(os.environ.get("LOCALAPPDATA", Path.home()))\n            / "AoE2Overlay"\n        )\n\n        def preparar():\n            DATA_DIR.mkdir(parents=True, exist_ok=True)\n            destino = DATA_DIR / "icones_aoe2"\n            destino.mkdir(exist_ok=True)\n\n            for origem in (BUNDLE_DIR / "icones_aoe2").iterdir():\n                alvo = destino / origem.name\n                if origem.is_file() and not alvo.exists():\n                    shutil.copy2(origem, alvo)\n    ')
    gravar(fonte / 'iniciar.py', '\n        import ctypes\n        import logging\n        import os\n        import sys\n        import traceback\n        from caminhos_app import DATA_DIR, preparar\n\n        def main():\n            preparar()\n            os.chdir(DATA_DIR)\n            logging.basicConfig(\n                filename=DATA_DIR / "aplicativo.log",\n                level=logging.INFO,\n                encoding="utf-8",\n            )\n\n            from idiomas_app import instalar\n            instalar()\n            import painel_jogadores as painel\n\n            if not painel.app.base.g.find_browser():\n                raise RuntimeError(\n                    "Instale Microsoft Edge ou Google Chrome "\n                    "para gerar o minimapa."\n                )\n\n            native = painel.app.base.Native()\n            root = painel.tk.Tk()\n            from caminhos_app import BUNDLE_DIR\n            root.iconbitmap(default=str(BUNDLE_DIR / "icone.ico"))\n\n            def erro_interface(tipo, valor, tb):\n                logging.error(\n                    "Erro na interface",\n                    exc_info=(tipo, valor, tb),\n                )\n                from tkinter import messagebox\n                messagebox.showerror(\n                    "AoE2 Overlay",\n                    f"{valor}\\n\\nLogs: {DATA_DIR}",\n                    parent=root,\n                )\n\n            root.report_callback_exception = erro_interface\n            painel.Window(root, native)\n            root.mainloop()\n\n        if __name__ == "__main__":\n            try:\n                main()\n            except Exception:\n                detalhes = traceback.format_exc()\n                DATA_DIR.mkdir(parents=True, exist_ok=True)\n                with (DATA_DIR / "falha_inicializacao.log").open(\n                    "a", encoding="utf-8"\n                ) as arquivo:\n                    arquivo.write(detalhes + "\\n")\n                ctypes.windll.user32.MessageBoxW(\n                    None,\n                    detalhes + f"\\nLogs: {DATA_DIR}",\n                    "AoE2 Overlay — erro",\n                    0x10,\n                )\n                sys.exit(1)\n    ')
    gravar(trabalho / 'requirements.txt', '\n        mgz @ https://github.com/Stephenwb1/aoc-mgz/archive/ab223cd95f7ddd2f79954d9aa4ae248b6ff61c31.zip\n        aocref==2.0.42\n        construct==2.8.16\n        tabulate==0.10.0\n        websocket-client==1.9.0\n        pyinstaller==6.16.0\nqrcode==8.2\nPillow==11.3.0\n')
    ambiente = trabalho / 'venv'
    executar(sys.executable, '-m', 'venv', ambiente)
    python = ambiente / 'Scripts' / 'python.exe'
    print('\nInstalando dependências de compilação...')
    executar(python, '-m', 'pip', 'install', '-r', trabalho / 'requirements.txt')
    print('\nGerando executável...')
    comando = [python, '-m', 'PyInstaller', '--noconfirm', '--clean', '--windowed', '--onedir', '--noupx', '--name', 'AoE2Overlay', '--distpath', trabalho / 'dist', '--workpath', trabalho / 'build', '--specpath', trabalho, '--paths', fonte, '--add-data', f"{fonte / 'icones_aoe2'};icones_aoe2", '--collect-all', 'qrcode', '--collect-all', 'PIL', '--icon', fonte / 'icone.ico', '--add-data', str(fonte / 'icone.ico') + ';.']
    for pacote in ('mgz', 'aocref', 'construct', 'websocket', 'tabulate'):
        comando.extend(['--collect-all', pacote])
    comando.append(fonte / 'iniciar.py')
    executar(*comando)
    if somente_executavel_patch:
        import json
        resultado = {'dist': str(trabalho / 'dist' / 'AoE2Overlay'), 'python_build': str(python)}
        (projeto / 'ultimo_build_patch.json').write_text(json.dumps(resultado), encoding='utf-8')
        print('Build para patch concluído:', resultado['dist'])
        return
    gravar(trabalho / 'instalador.iss', '\ufeff[Setup]\nShowLanguageDialog=yes\nUsePreviousLanguage=yes\nLanguageDetectionMethod=uilanguage\nSetupIconFile=src\\icone.ico\nAppId={{9EDE4C65-EF83-4B8E-B804-20DD623EE0B6}\nAppName=AoE2 Overlay\nAppVersion=0.1.0\nDefaultDirName={localappdata}\\Programs\\AoE2Overlay\nDefaultGroupName=AoE2 Overlay\nPrivilegesRequired=lowest\nArchitecturesAllowed=x64compatible\nArchitecturesInstallIn64BitMode=x64compatible\nOutputDir=instalador\nOutputBaseFilename=AoE2Overlay-Setup-0.1.0\nCompression=lzma2\nSolidCompression=yes\nWizardStyle=modern\nUninstallDisplayIcon={app}\\AoE2Overlay.exe\n\n[Languages]\nName: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"\nName: "english"; MessagesFile: "compiler:Default.isl"\nName: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"\n\n[Tasks]\nName: "desktopicon"; Description: "{cm:AppDesktop}"; Flags: unchecked\n\n[Files]\nSource: "dist\\AoE2Overlay\\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs\n\n[Icons]\nName: "{group}\\AoE2 Overlay"; Filename: "{app}\\AoE2Overlay.exe"\nName: "{autodesktop}\\AoE2 Overlay"; Filename: "{app}\\AoE2Overlay.exe"; Tasks: desktopicon\n\n[Run]\nFilename: "{app}\\AoE2Overlay.exe"; Description: "{cm:AppLaunch}"; Flags: nowait postinstall skipifsilent\n\n\n; I18N033\n[Registry]\nRoot: HKCU; Subkey: "Software\\AoE2Overlay"; ValueType: string; ValueName: "Language"; ValueData: "{code:IdiomaSelecionado}"\n\n[CustomMessages]\nbrazilianportuguese.AppLanguageTitle=Idioma do aplicativo\nbrazilianportuguese.AppLanguageDescription=Escolha o idioma da interface, Ajuda e painel móvel.\nbrazilianportuguese.AppLanguagePrompt=Idioma do aplicativo (a escolha anterior é mantida nas atualizações):\nbrazilianportuguese.AppDesktop=Criar atalho na área de trabalho\nbrazilianportuguese.AppLaunch=Abrir AoE2 Overlay\nenglish.AppLanguageTitle=Application language\nenglish.AppLanguageDescription=Choose the language for the interface, help and mobile panel.\nenglish.AppLanguagePrompt=Application language (your previous choice is retained during updates):\nenglish.AppDesktop=Create a desktop shortcut\nenglish.AppLaunch=Launch AoE2 Overlay\nspanish.AppLanguageTitle=Idioma de la aplicación\nspanish.AppLanguageDescription=Elija el idioma de la interfaz, la ayuda y el panel móvil.\nspanish.AppLanguagePrompt=Idioma de la aplicación (se conserva la selección anterior al actualizar):\nspanish.AppDesktop=Crear un acceso directo en el escritorio\nspanish.AppLaunch=Abrir AoE2 Overlay\n\n[Code]\nvar\n  PaginaIdioma: TWizardPage;\n  ListaIdioma: TNewComboBox;\n\nfunction IdiomaSelecionado(Param: String): String;\nbegin\n  Result := \'pt\';\n  case ListaIdioma.ItemIndex of\n    0: Result := \'pt\';\n    1: Result := \'en\';\n    2: Result := \'es\';\n    3: Result := \'zh-CN\';\n    4: Result := \'zh-TW\';\n    5: Result := \'ja\';\n    6: Result := \'ko\';\n    7: Result := \'hi\';\n    8: Result := \'bn\';\n    9: Result := \'mr\';\n    10: Result := \'te\';\n    11: Result := \'ta\';\n    12: Result := \'ur\';\n    13: Result := \'pa\';\n    14: Result := \'gu\';\n    15: Result := \'ne\';\n    16: Result := \'si\';\n    17: Result := \'th\';\n    18: Result := \'vi\';\n    19: Result := \'id\';\n    20: Result := \'ms\';\n    21: Result := \'tl\';\n    22: Result := \'my\';\n    23: Result := \'km\';\n    24: Result := \'lo\';\n    25: Result := \'ar\';\n    26: Result := \'fa\';\n    27: Result := \'tr\';\n    28: Result := \'ru\';\n    29: Result := \'kk\';\n    30: Result := \'uz\';\n    31: Result := \'mn\';\n    32: Result := \'az\';\n    33: Result := \'hy\';\n    34: Result := \'ka\';\n    35: Result := \'he\';\n  end;\nend;\n\nprocedure InitializeWizard;\nvar\n  Anterior: String;\n  I: Integer;\nbegin\n  PaginaIdioma := CreateCustomPage(wpSelectDir,\n    ExpandConstant(\'{cm:AppLanguageTitle}\'),\n    ExpandConstant(\'{cm:AppLanguageDescription}\'));\n  with TNewStaticText.Create(PaginaIdioma) do\n  begin\n    Parent := PaginaIdioma.Surface;\n    Left := 0;\n    Top := 0;\n    Width := PaginaIdioma.SurfaceWidth;\n    Height := ScaleY(36);\n    AutoSize := False;\n    WordWrap := True;\n    Caption := ExpandConstant(\'{cm:AppLanguagePrompt}\');\n  end;\n  ListaIdioma := TNewComboBox.Create(PaginaIdioma);\n  ListaIdioma.Parent := PaginaIdioma.Surface;\n  ListaIdioma.Left := 0;\n  ListaIdioma.Top := ScaleY(42);\n  ListaIdioma.Width := PaginaIdioma.SurfaceWidth;\n  ListaIdioma.Style := csDropDownList;\n  ListaIdioma.Items.Add(\'Português (Brasil)\');\n  ListaIdioma.Items.Add(\'English\');\n  ListaIdioma.Items.Add(\'Español\');\n  ListaIdioma.Items.Add(\'简体中文 · Chinese (Simplified)\');\n  ListaIdioma.Items.Add(\'繁體中文 · Chinese (Traditional)\');\n  ListaIdioma.Items.Add(\'日本語 · Japanese\');\n  ListaIdioma.Items.Add(\'한국어 · Korean\');\n  ListaIdioma.Items.Add(\'हिन्दी · Hindi\');\n  ListaIdioma.Items.Add(\'বাংলা · Bengali\');\n  ListaIdioma.Items.Add(\'मराठी · Marathi\');\n  ListaIdioma.Items.Add(\'తెలుగు · Telugu\');\n  ListaIdioma.Items.Add(\'தமிழ் · Tamil\');\n  ListaIdioma.Items.Add(\'اردو · Urdu\');\n  ListaIdioma.Items.Add(\'ਪੰਜਾਬੀ · Punjabi\');\n  ListaIdioma.Items.Add(\'ગુજરાતી · Gujarati\');\n  ListaIdioma.Items.Add(\'नेपाली · Nepali\');\n  ListaIdioma.Items.Add(\'සිංහල · Sinhala\');\n  ListaIdioma.Items.Add(\'ไทย · Thai\');\n  ListaIdioma.Items.Add(\'Tiếng Việt · Vietnamese\');\n  ListaIdioma.Items.Add(\'Bahasa Indonesia\');\n  ListaIdioma.Items.Add(\'Bahasa Melayu\');\n  ListaIdioma.Items.Add(\'Filipino\');\n  ListaIdioma.Items.Add(\'မြန်မာ · Burmese\');\n  ListaIdioma.Items.Add(\'ខ្មែរ · Khmer\');\n  ListaIdioma.Items.Add(\'ລາວ · Lao\');\n  ListaIdioma.Items.Add(\'العربية · Arabic\');\n  ListaIdioma.Items.Add(\'فارسی · Persian\');\n  ListaIdioma.Items.Add(\'Türkçe · Turkish\');\n  ListaIdioma.Items.Add(\'Русский · Russian\');\n  ListaIdioma.Items.Add(\'Қазақша · Kazakh\');\n  ListaIdioma.Items.Add(\'Oʻzbekcha · Uzbek\');\n  ListaIdioma.Items.Add(\'Монгол · Mongolian\');\n  ListaIdioma.Items.Add(\'Azərbaycan dili\');\n  ListaIdioma.Items.Add(\'Հայերեն · Armenian\');\n  ListaIdioma.Items.Add(\'ქართული · Georgian\');\n  ListaIdioma.Items.Add(\'עברית · Hebrew\');\n  ListaIdioma.ItemIndex := 0;\n  if ActiveLanguage = \'english\' then ListaIdioma.ItemIndex := 1;\n  if ActiveLanguage = \'spanish\' then ListaIdioma.ItemIndex := 2;\n  if RegQueryStringValue(HKCU, \'Software\\AoE2Overlay\', \'Language\', Anterior) then\n  begin\n    for I := 0 to ListaIdioma.Items.Count - 1 do\n    begin\n      ListaIdioma.ItemIndex := I;\n      if IdiomaSelecionado(\'\') = Anterior then Break;\n    end;\n    if IdiomaSelecionado(\'\') <> Anterior then ListaIdioma.ItemIndex := 0;\n  end;\nend;\n')
    print('\nGerando instalador...')
    executar(compilador, trabalho / 'instalador.iss')
    instalador = trabalho / 'instalador' / 'AoE2Overlay-Setup-0.1.0.exe'
    if not instalador.is_file():
        raise RuntimeError('O instalador não foi encontrado.')
    print('\nInstalador gerado com sucesso:')
    print(instalador)
    os.startfile(str(instalador.parent))
if __name__ == '__main__':
    try:
        main()
    except Exception as erro:
        print(f'\nERRO: {erro}')
        sys.exit(1)
