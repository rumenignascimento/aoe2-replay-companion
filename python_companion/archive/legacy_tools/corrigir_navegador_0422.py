import ast,base64,shutil
from pathlib import Path
from datetime import datetime
PAYLOAD='IiIiSW5pY2lhbGl6YcOnw6NvIGlzb2xhZGEgZGUgRWRnZS9DaHJvbWUgZSBkaWFnbsOzc3RpY28gZG8gcmVuZGVyaXphZG9yIFBORy4iIiIKZnJvbSBwYXRobGliIGltcG9ydCBQYXRoCmltcG9ydCBjdHlwZXMsbG9nZ2luZyxvcyxzaHV0aWwsc3VicHJvY2VzcyxzeXMsdGhyZWFkaW5nCkxPQ0s9dGhyZWFkaW5nLlJMb2NrKCkKCgpkZWYgY2FuZGlkYXRlcyhmaXJzdD1Ob25lKToKICAgIHJlc3VsdD1bXQogICAgZGVmIGFkZChwYXRoKToKICAgICAgICBpZiBwYXRoIGFuZCBQYXRoKHBhdGgpLmlzX2ZpbGUoKSBhbmQgb3MucGF0aC5ub3JtY2FzZShzdHIocGF0aCkpIG5vdCBpbiB7b3MucGF0aC5ub3JtY2FzZShwKSBmb3IgcCBpbiByZXN1bHR9OnJlc3VsdC5hcHBlbmQoc3RyKHBhdGgpKQogICAgYWRkKGZpcnN0KQogICAgZm9yIGtleSBpbiAoJ1BST0dSQU1GSUxFUycsJ1BST0dSQU1GSUxFUyhYODYpJywnTE9DQUxBUFBEQVRBJyk6CiAgICAgICAgaWYgb3MuZW52aXJvbi5nZXQoa2V5KToKICAgICAgICAgICAgZm9yIHN1ZmZpeCBpbiAoJ01pY3Jvc29mdC9FZGdlL0FwcGxpY2F0aW9uL21zZWRnZS5leGUnLCdHb29nbGUvQ2hyb21lL0FwcGxpY2F0aW9uL2Nocm9tZS5leGUnKToKICAgICAgICAgICAgICAgIGFkZChQYXRoKG9zLmVudmlyb25ba2V5XSkvc3VmZml4KQogICAgZm9yIG5hbWUgaW4gKCdtc2VkZ2UnLCdjaHJvbWUnLCdjaHJvbWl1bScsJ2Nocm9taXVtLWJyb3dzZXInLCdnb29nbGUtY2hyb21lJyk6YWRkKHNodXRpbC53aGljaChuYW1lKSkKICAgIHJldHVybiByZXN1bHQKCgpkZWYgY2xlYW5fZW52aXJvbm1lbnQoKToKICAgIGVudj1vcy5lbnZpcm9uLmNvcHkoKQogICAgaWYgZ2V0YXR0cihzeXMsJ2Zyb3plbicsRmFsc2UpOgogICAgICAgIGJ1bmRsZT1nZXRhdHRyKHN5cywnX01FSVBBU1MnLE5vbmUpCiAgICAgICAgaWYgYnVuZGxlOgogICAgICAgICAgICBiYXNlPVBhdGgoYnVuZGxlKS5yZXNvbHZlKCkKICAgICAgICAgICAgaXRlbXM9W10KICAgICAgICAgICAgZm9yIGl0ZW0gaW4gZW52LmdldCgnUEFUSCcsJycpLnNwbGl0KG9zLnBhdGhzZXApOgogICAgICAgICAgICAgICAgdHJ5Omluc2lkZT1QYXRoKGl0ZW0pLnJlc29sdmUoKS5pc19yZWxhdGl2ZV90byhiYXNlKQogICAgICAgICAgICAgICAgZXhjZXB0IChPU0Vycm9yLFZhbHVlRXJyb3IpOmluc2lkZT1GYWxzZQogICAgICAgICAgICAgICAgaWYgbm90IGluc2lkZTppdGVtcy5hcHBlbmQoaXRlbSkKICAgICAgICAgICAgZW52WydQQVRIJ109b3MucGF0aHNlcC5qb2luKGl0ZW1zKQogICAgICAgIGlmIHN5cy5wbGF0Zm9ybSE9J3dpbjMyJzoKICAgICAgICAgICAgb3JpZ2luYWw9ZW52LmdldCgnTERfTElCUkFSWV9QQVRIX09SSUcnKQogICAgICAgICAgICBpZiBvcmlnaW5hbCBpcyBOb25lOmVudi5wb3AoJ0xEX0xJQlJBUllfUEFUSCcsTm9uZSkKICAgICAgICAgICAgZWxzZTplbnZbJ0xEX0xJQlJBUllfUEFUSCddPW9yaWdpbmFsCiAgICByZXR1cm4gZW52CgoKZGVmIGxhdW5jaChjb21tYW5kLHN0ZGVycik6CiAgICBlbnY9Y2xlYW5fZW52aXJvbm1lbnQoKQogICAgIyBQeUluc3RhbGxlciByZWRpcmVjdHMgRExMIHNlYXJjaCB0byBpdHMgYnVuZGxlLiBFeHRlcm5hbCBicm93c2VycyBuZWVkIHRoZQogICAgIyBub3JtYWwgV2luZG93cyBETEwgc2VhcmNoLiBSZXN0b3JlIHRoZSBhcHBsaWNhdGlvbidzIHNldHRpbmcgaW1tZWRpYXRlbHkuCiAgICB3aXRoIExPQ0s6CiAgICAgICAga2VybmVsPU5vbmU7cHJldmlvdXM9Tm9uZQogICAgICAgIHRyeToKICAgICAgICAgICAgaWYgc3lzLnBsYXRmb3JtPT0nd2luMzInIGFuZCBnZXRhdHRyKHN5cywnZnJvemVuJyxGYWxzZSk6CiAgICAgICAgICAgICAgICBmcm9tIGN0eXBlcyBpbXBvcnQgd2ludHlwZXMKICAgICAgICAgICAgICAgIGtlcm5lbD1jdHlwZXMuV2luRExMKCdrZXJuZWwzMicsdXNlX2xhc3RfZXJyb3I9VHJ1ZSkKICAgICAgICAgICAgICAgIGtlcm5lbC5HZXREbGxEaXJlY3RvcnlXLmFyZ3R5cGVzPSh3aW50eXBlcy5EV09SRCx3aW50eXBlcy5MUFdTVFIpCiAgICAgICAgICAgICAgICBrZXJuZWwuR2V0RGxsRGlyZWN0b3J5Vy5yZXN0eXBlPXdpbnR5cGVzLkRXT1JECiAgICAgICAgICAgICAgICBrZXJuZWwuU2V0RGxsRGlyZWN0b3J5Vy5hcmd0eXBlcz0od2ludHlwZXMuTFBDV1NUUiwpCiAgICAgICAgICAgICAgICBrZXJuZWwuU2V0RGxsRGlyZWN0b3J5Vy5yZXN0eXBlPXdpbnR5cGVzLkJPT0wKICAgICAgICAgICAgICAgIGJ1ZmZlcj1jdHlwZXMuY3JlYXRlX3VuaWNvZGVfYnVmZmVyKDMyNzY4KQogICAgICAgICAgICAgICAgY291bnQ9a2VybmVsLkdldERsbERpcmVjdG9yeVcobGVuKGJ1ZmZlciksYnVmZmVyKQogICAgICAgICAgICAgICAgaWYgY291bnQ+PWxlbihidWZmZXIpOnJhaXNlIE9TRXJyb3IoJ0RpcmV0w7NyaW8gZGUgRExMIGV4Y2VkZSBvIGxpbWl0ZS4nKQogICAgICAgICAgICAgICAgcHJldmlvdXM9YnVmZmVyLnZhbHVlIGlmIGNvdW50IGVsc2UgTm9uZQogICAgICAgICAgICAgICAgaWYgbm90IGtlcm5lbC5TZXREbGxEaXJlY3RvcnlXKE5vbmUpOnJhaXNlIGN0eXBlcy5XaW5FcnJvcihjdHlwZXMuZ2V0X2xhc3RfZXJyb3IoKSkKICAgICAgICAgICAgcmV0dXJuIHN1YnByb2Nlc3MuUG9wZW4oY29tbWFuZCxzdGRvdXQ9c3VicHJvY2Vzcy5ERVZOVUxMLHN0ZGVycj1zdGRlcnIsZW52PWVudiwKICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgICAgY3JlYXRpb25mbGFncz1nZXRhdHRyKHN1YnByb2Nlc3MsJ0NSRUFURV9OT19XSU5ET1cnLDApKQogICAgICAgIGZpbmFsbHk6CiAgICAgICAgICAgIGlmIGtlcm5lbCBpcyBub3QgTm9uZSBhbmQgbm90IGtlcm5lbC5TZXREbGxEaXJlY3RvcnlXKHByZXZpb3VzKTpsb2dnaW5nLmVycm9yKCdGYWxoYSBhbyByZXN0YXVyYXIgZGlyZXTDs3JpbyBkZSBETEwgZG8gYXBsaWNhdGl2by4nKQoKCmRlZiByZXBvcnRfZmFpbHVyZShicm93c2VyLHByb2Nlc3Msc3RkZXJyX3BhdGgpOgogICAgdHJ5OgogICAgICAgIHdpdGggUGF0aChzdGRlcnJfcGF0aCkub3BlbigncmInKSBhcyBmOgogICAgICAgICAgICBmLnNlZWsoMCwyKTtzaXplPWYudGVsbCgpO2Yuc2VlayhtYXgoMCxzaXplLTEyMDAwKSk7dGFpbD1mLnJlYWQoKS5kZWNvZGUoJ3V0Zi04JyxlcnJvcnM9J3JlcGxhY2UnKQogICAgZXhjZXB0IE9TRXJyb3I6dGFpbD0nTsOjbyBmb2kgcG9zc8OtdmVsIGxlciBzdGRlcnIgZG8gbmF2ZWdhZG9yLicKICAgIGNvZGU9cHJvY2Vzcy5yZXR1cm5jb2RlIGlmIHByb2Nlc3MgaXMgbm90IE5vbmUgZWxzZSAnbsOjbyBpbmljaWFkbycKICAgIG1lc3NhZ2U9J05hdmVnYWRvciBQTkc6ICcrc3RyKGJyb3dzZXIpKydcbkPDs2RpZ28gZGUgc2HDrWRhOiAnK3N0cihjb2RlKSsnXG4nK3RhaWwKICAgIGxvZ2dpbmcuZXJyb3IoJyVzJyxtZXNzYWdlKQogICAgdHJ5OgogICAgICAgIGRpcmVjdG9yeT1QYXRoKG9zLmVudmlyb24uZ2V0KCdMT0NBTEFQUERBVEEnLFBhdGguaG9tZSgpKSkvJ0FvRTJPdmVybGF5JztkaXJlY3RvcnkubWtkaXIocGFyZW50cz1UcnVlLGV4aXN0X29rPVRydWUpCiAgICAgICAgKGRpcmVjdG9yeS8nbmF2ZWdhZG9yX2RpYWdub3N0aWNvLmxvZycpLndyaXRlX3RleHQobWVzc2FnZSxlbmNvZGluZz0ndXRmLTgnKQogICAgZXhjZXB0IE9TRXJyb3I6bG9nZ2luZy5leGNlcHRpb24oJ0ZhbGhhIGFvIHNhbHZhciBkaWFnbsOzc3RpY28gZG8gbmF2ZWdhZG9yIFBORycpCgoKZGVmIGV4cG9ydF93aXRoX2ZhbGxiYWNrKHN2ZyxwbmcsZmluZF9icm93c2VyLGV4cG9ydF9vbmUpOgogICAgYnJvd3NlcnM9Y2FuZGlkYXRlcyhmaW5kX2Jyb3dzZXIoKSkKICAgIGlmIG5vdCBicm93c2VyczpyYWlzZSBSdW50aW1lRXJyb3IoJ0VkZ2UvQ2hyb21lIG7Do28gZW5jb250cmFkby4gSW5zdGFsZSB1bSBuYXZlZ2Fkb3IgY29tcGF0w612ZWwgcGFyYSBnZXJhciBvIG1pbmltYXBhLicpCiAgICBmYWlsdXJlcz1bXQogICAgZm9yIGJyb3dzZXIgaW4gYnJvd3NlcnM6CiAgICAgICAgdHJ5OnJldHVybiBleHBvcnRfb25lKHN2ZyxwbmcsYnJvd3NlcikKICAgICAgICBleGNlcHQgRXhjZXB0aW9uIGFzIGV4YzoKICAgICAgICAgICAgbG9nZ2luZy5leGNlcHRpb24oJ0ZhbGhhIG5vIHJlbmRlcml6YWRvciBjb20gJXMnLGJyb3dzZXIpCiAgICAgICAgICAgIGZhaWx1cmVzLmFwcGVuZChQYXRoKGJyb3dzZXIpLm5hbWUrJzogJytzdHIoZXhjKSkKICAgIHJhaXNlIFJ1bnRpbWVFcnJvcignRmFsaGEgYW8gZ2VyYXIgYSBpbWFnZW0gY29tIG9zIG5hdmVnYWRvcmVzIGVuY29udHJhZG9zLiBDb25zdWx0ZSBhcGxpY2F0aXZvLmxvZyBlIG5hdmVnYWRvcl9kaWFnbm9zdGljby5sb2cgZW0gJUxPQ0FMQVBQREFUQSVcXEFvRTJPdmVybGF5LiDDmmx0aW1vIGVycm86ICcrZmFpbHVyZXNbLTFdKQo='

def add_import(tree,module,alias=None):
    if any(isinstance(n,ast.Import) and any(a.name==module for a in n.names) for n in tree.body):return
    index=0
    for i,n in enumerate(tree.body):
        if i==0 and isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):index=i+1
        elif isinstance(n,ast.ImportFrom) and n.module=='__future__':index=i+1
        else:break
    tree.body.insert(index,ast.Import(names=[ast.alias(name=module,asname=alias)]))

def gerador(source):
    tree=ast.parse(source)
    if any(isinstance(n,ast.FunctionDef) and n.name=='_export_png_once_0422' for n in tree.body):return source
    fn=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='export_png'),None)
    if fn is None:raise ValueError('export_png não encontrada.')
    if len(fn.args.args)!=2:raise ValueError('Assinatura do renderizador não reconhecida.')
    fn.name='_export_png_once_0422';fn.args.args.append(ast.arg(arg='browser'))
    first=fn.body[0]
    if not isinstance(first,ast.Assign) or ast.unparse(first.value)!='find_browser()':raise ValueError('Busca do navegador não reconhecida.')
    fn.body.pop(0)
    with_node=next((n for n in fn.body if isinstance(n,ast.With)),None)
    if with_node is None:raise ValueError('Perfil temporário do navegador não reconhecido.')
    launch_index=next((i for i,n in enumerate(with_node.body) if isinstance(n,ast.Assign) and ast.unparse(n.targets[0])=='process' and isinstance(n.value,ast.Call)),None)
    if launch_index is None:raise ValueError('Inicialização do processo não reconhecida.')
    launch=ast.parse("""stderr_path = Path(profile) / 'browser-stderr.log'
stream = stderr_path.open('wb')
process = None
success = False
try:
    process = _png_backend_0422.launch(command, stream)
except Exception:
    stream.close()
    _png_backend_0422.report_failure(browser, process, stderr_path)
    raise
""").body
    with_node.body[launch_index:launch_index+1]=launch
    attempt=next((n for n in with_node.body if isinstance(n,ast.Try) and n.finalbody),None)
    if attempt is None:raise ValueError('Encerramento do navegador não reconhecido.')
    attempt.body.append(ast.parse('success = True').body[0])
    attempt.finalbody=[ast.Try(body=attempt.finalbody,handlers=[],orelse=[],finalbody=ast.parse("""stream.close()
if not success:
    _png_backend_0422.report_failure(browser, process, stderr_path)
""").body)]
    tree.body.insert(tree.body.index(fn)+1,ast.parse("""def export_png(svg, png):
    return _png_backend_0422.export_with_fallback(svg, png, find_browser, _export_png_once_0422)
""").body[0])
    add_import(tree,'navegador_png_0422','_png_backend_0422')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'

def overlay(source):
    tree=ast.parse(source);changed=False
    for n in ast.walk(tree):
        if isinstance(n,ast.FunctionDef) and n.name=='job':
            for handler in [x for x in ast.walk(n) if isinstance(x,ast.ExceptHandler) and isinstance(x.type,ast.Name) and x.type.id=='Exception']:
                if not any('Falha no processamento do minimapa' in ast.unparse(x) for x in handler.body):
                    handler.body.insert(0,ast.parse("__import__('logging').exception('Falha no processamento do minimapa')").body[0])
                changed=True
    if not changed:raise ValueError('Processamento do overlay não reconhecido.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'

def instalador(source):
    tree=ast.parse(source);found=False
    for n in ast.walk(tree):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='arquivos' for t in n.targets) and isinstance(n.value,ast.List):
            values=[getattr(x,'value',None) for x in n.value.elts]
            if 'gerador_mapa.py' in values:
                found=True
                if 'navegador_png_0422.py' not in values:n.value.elts.append(ast.Constant(value='navegador_png_0422.py'))
    if not found:raise ValueError('Módulos do instalador não reconhecidos.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'

def main():
    root=Path(__file__).resolve().parent;results={}
    for name,adapt in [('gerador_mapa.py',gerador),('mapa_overlay.py',overlay),('gerar_instalador.py',instalador)]:
        path=root/name
        if not path.is_file():raise ValueError('Arquivo ausente: '+name+'. Salve o atualizador na pasta GeradorMapaAoE2.')
        results[name]=adapt(path.read_text(encoding='utf-8-sig'))
    results['navegador_png_0422.py']=base64.b64decode(PAYLOAD).decode('utf-8')
    for name,code in results.items():compile(code,name,'exec')
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    existed={n:(root/n).is_file() for n in results}
    for n in results:
        if existed[n]:shutil.copy2(root/n,backup/n)
    try:
        for n,code in results.items():
            temp=root/(n+'.tmp');temp.write_text(code,encoding='utf-8');temp.replace(root/n)
    except Exception:
        for n in results:
            if existed[n]:shutil.copy2(backup/n,root/n)
            else:(root/n).unlink(missing_ok=True)
        raise
    print('Inicialização do navegador ajustada e diagnóstico habilitado. Backup:',backup)
    print('Gere o próximo patch: py -3.12 gerar_patch.py')
    print('Se0.4.21 está instalada, use base0.4.21 e nova0.4.22. Depois aplique e teste um replay antes de publicar.')
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
