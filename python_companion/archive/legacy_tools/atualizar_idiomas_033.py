"""Instala catálogos offline e integra o idioma ao instalador existente."""
import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


def preparar_iss(texto, languages):
    if '; I18N033' in texto:
        return texto
    texto = '\n'.join(line.strip() for line in texto.splitlines()) + '\n'
    if '[Code]' in texto or '[Registry]' in texto or '[CustomMessages]' in texto:
        raise RuntimeError('O instalador contém seções adicionais que precisam ser integradas. Nenhum arquivo alterado.')
    language_section = '''[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\\Spanish.isl"

'''
    texto, count = re.subn(r'\[Languages\][\s\S]*?(?=\[|\Z)', lambda m: language_section, texto, count=1)
    if count != 1:
        raise RuntimeError('Seção de idiomas não reconhecida.')
    texto = texto.replace('[Setup]', '[Setup]\nShowLanguageDialog=yes\nUsePreviousLanguage=yes\nLanguageDetectionMethod=uilanguage', 1)
    texto = texto.replace('Description: "Criar atalho na área de trabalho"', 'Description: "{cm:AppDesktop}"')
    texto = texto.replace('Description: "Abrir AoE2 Overlay"', 'Description: "{cm:AppLaunch}"')
    texto += '''
; I18N033
[Registry]
Root: HKCU; Subkey: "Software\\AoE2Overlay"; ValueType: string; ValueName: "Language"; ValueData: "{code:IdiomaSelecionado}"

[CustomMessages]
brazilianportuguese.AppLanguageTitle=Idioma do aplicativo
brazilianportuguese.AppLanguageDescription=Escolha o idioma da interface, Ajuda e painel móvel.
brazilianportuguese.AppLanguagePrompt=Idioma do aplicativo (a escolha anterior é mantida nas atualizações):
brazilianportuguese.AppDesktop=Criar atalho na área de trabalho
brazilianportuguese.AppLaunch=Abrir AoE2 Overlay
english.AppLanguageTitle=Application language
english.AppLanguageDescription=Choose the language for the interface, help and mobile panel.
english.AppLanguagePrompt=Application language (your previous choice is retained during updates):
english.AppDesktop=Create a desktop shortcut
english.AppLaunch=Launch AoE2 Overlay
spanish.AppLanguageTitle=Idioma de la aplicación
spanish.AppLanguageDescription=Elija el idioma de la interfaz, la ayuda y el panel móvil.
spanish.AppLanguagePrompt=Idioma de la aplicación (se conserva la selección anterior al actualizar):
spanish.AppDesktop=Crear un acceso directo en el escritorio
spanish.AppLaunch=Abrir AoE2 Overlay

[Code]
var
  PaginaIdioma: TWizardPage;
  ListaIdioma: TNewComboBox;

function IdiomaSelecionado(Param: String): String;
begin
  Result := 'pt';
  case ListaIdioma.ItemIndex of
'''
    for index, (code, name) in enumerate(languages):
        texto += "    %d: Result := '%s';\n" % (index, code)
    texto += '''  end;
end;

procedure InitializeWizard;
var
  Anterior: String;
  I: Integer;
begin
  PaginaIdioma := CreateCustomPage(wpSelectDir,
    ExpandConstant('{cm:AppLanguageTitle}'),
    ExpandConstant('{cm:AppLanguageDescription}'));
  with TNewStaticText.Create(PaginaIdioma) do
  begin
    Parent := PaginaIdioma.Surface;
    Left := 0;
    Top := 0;
    Width := PaginaIdioma.SurfaceWidth;
    Height := ScaleY(36);
    AutoSize := False;
    WordWrap := True;
    Caption := ExpandConstant('{cm:AppLanguagePrompt}');
  end;
  ListaIdioma := TNewComboBox.Create(PaginaIdioma);
  ListaIdioma.Parent := PaginaIdioma.Surface;
  ListaIdioma.Left := 0;
  ListaIdioma.Top := ScaleY(42);
  ListaIdioma.Width := PaginaIdioma.SurfaceWidth;
  ListaIdioma.Style := csDropDownList;
'''
    for code, name in languages:
        texto += "  ListaIdioma.Items.Add('%s');\n" % name.replace("'", "''")
    texto += '''  ListaIdioma.ItemIndex := 0;
  if ActiveLanguage = 'english' then ListaIdioma.ItemIndex := 1;
  if ActiveLanguage = 'spanish' then ListaIdioma.ItemIndex := 2;
  if RegQueryStringValue(HKCU, 'Software\\AoE2Overlay', 'Language', Anterior) then
  begin
    for I := 0 to ListaIdioma.Items.Count - 1 do
    begin
      ListaIdioma.ItemIndex := I;
      if IdiomaSelecionado('') = Anterior then Break;
    end;
    if IdiomaSelecionado('') <> Anterior then ListaIdioma.ItemIndex := 0;
  end;
end;
'''
    return "\ufeff" + texto.lstrip()


def modificar_gerador(codigo, languages):
    tree = ast.parse(codigo)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.List):
            names = [v.value for v in node.elts if isinstance(v, ast.Constant) and isinstance(v.value, str)]
            if 'painel_jogadores.py' in names and 'central_replay.py' in names:
                found.add('files')
                for name in ('idiomas_app.py', 'catalogo_idiomas.py'):
                    if name not in names:
                        node.elts.append(ast.Constant(name))
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if '[Setup]' in node.value and '[Languages]' in node.value:
                node.value = preparar_iss(node.value, languages)
                found.add('iss')
            elif 'from caminhos_app import DATA_DIR, preparar' in node.value and 'import painel_jogadores as painel' in node.value:
                if 'from idiomas_app import instalar' not in node.value:
                    node.value, count = re.subn(
                        r'(?m)^([ \t]*)import painel_jogadores as painel',
                        lambda m: m[1] + 'from idiomas_app import instalar\n' + m[1] + 'instalar()\n' + m.group(), node.value, count=1)
                    if count != 1:
                        raise RuntimeError('Inicialização não reconhecida.')
                ast.parse(__import__('textwrap').dedent(node.value).lstrip())
                found.add('startup')
    if found != {'files', 'iss', 'startup'}:
        raise RuntimeError('Estrutura do gerador diferente do esperado: ' + str(found))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def main():
    root = Path(__file__).resolve().parent
    required = ('gerar_instalador.py', 'gerar_atualizacao.py', 'central_replay.py',
                'ajuda_replay.py', 'painel_movel.py', 'idiomas_app.py', 'catalogo_idiomas.py')
    for name in required:
        if not (root / name).is_file():
            raise RuntimeError('Arquivo ausente: ' + name + '. Extraia o pacote completo na pasta do projeto.')
    # Somente constantes de dados; não executa o catálogo recebido.
    catalog_tree = ast.parse((root / 'catalogo_idiomas.py').read_text(encoding='utf-8-sig'))
    languages = next(ast.literal_eval(n.value) for n in catalog_tree.body
                     if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LANGUAGES' for t in n.targets))
    changes = {'gerar_instalador.py': modificar_gerador((root / 'gerar_instalador.py').read_text(encoding='utf-8-sig'), languages)}
    # Mantém a seleção válida também ao executar o código-fonte, sem instalador.
    source = (root / 'central_replay.py').read_text(encoding='utf-8-sig')
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr in ('body_font', 'title_font') for t in node.targets):
            if 'fonte_interface' not in ast.unparse(node.value):
                node.value = ast.Call(func=ast.Name(id='_fonte_interface', ctx=ast.Load()), args=[node.value], keywords=[])
    if 'from idiomas_app import fonte_interface as _fonte_interface' not in source:
        tree.body.insert(1, ast.parse('from idiomas_app import fonte_interface as _fonte_interface').body[0])
    ast.fix_missing_locations(tree)
    changes['central_replay.py'] = ast.unparse(tree) + '\n'
    tree = ast.parse((root / 'ajuda_replay.py').read_text(encoding='utf-8-sig'))
    found = False
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'instalar':
            if 'ajuda_localizada' not in ast.unparse(node):
                node.body[:0] = ast.parse('global TOPICS\nfrom idiomas_app import ajuda_localizada\nTOPICS = ajuda_localizada(TOPICS)').body
            found = True
    if not found:
        raise RuntimeError('Módulo Ajuda não reconhecido.')
    ast.fix_missing_locations(tree);changes['ajuda_replay.py'] = ast.unparse(tree) + '\n'
    tree = ast.parse((root / 'painel_movel.py').read_text(encoding='utf-8-sig'))
    source = ast.unparse(tree)
    if 'traduzir_html' not in source:
        index = next((i for i,n in enumerate(tree.body) if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'HTML' for t in n.targets)), None)
        if index is None:
            raise RuntimeError('Página móvel não reconhecida.')
        tree.body[index+1:index+1] = ast.parse('from idiomas_app import traduzir_html, tr\nHTML = traduzir_html(HTML)').body
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == 'message' and isinstance(node.value, ast.Constant) and node.value.value == 'Aguardando leitura da partida no PC…':
            node.value = ast.Call(func=ast.Name(id='tr', ctx=ast.Load()), args=[ast.Constant('Aguardando partida')], keywords=[])
    ast.fix_missing_locations(tree);changes['painel_movel.py'] = ast.unparse(tree) + '\n'
    for name, text in changes.items():
        ast.parse(text, filename=name)
    backup = root / 'backups_atualizacoes' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    for name in changes:
        shutil.copy2(root / name, backup / name)
    for name,text in changes.items():
        (root / name).write_text(text, encoding='utf-8')
    print('Idiomas integrados:', len(languages))
    print('Backup:', backup)
    print('Execute py -3.12 gerar_atualizacao.py e escolha 0.3.3 ou superior à última versão gerada.')


if __name__ == '__main__':
    try:
        main()
    except Exception as erro:
        print('ERRO:', erro)
        raise SystemExit(1)
