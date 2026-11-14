import ast
import shutil
from datetime import datetime
from pathlib import Path

DESENHO = "x=8+i*(tab_width+4)\nactive=window.panel_tab.get()==tab\nhover=getattr(window,'_click_tab_hover',None)==tab\npressed=getattr(window,'_click_tab_pressed',None)==tab\nfill='#674323' if active else '#e7cca0'\nif hover: fill='#75512f' if active else '#f1dcb8'\nif pressed: fill='#50331c'\ny=6+(1 if pressed else 0)\ncanvas.create_rectangle(x+1,8,x+tab_width+2,32,fill='#7a5a39',outline='',width=0)\ncanvas.create_rectangle(x,y,x+tab_width,y+23,fill=fill,outline='#65472b',width=1)\ninset=active or pressed\ntop='#3d2918' if inset else '#fff1cc'\nbottom='#dab77e' if inset else '#805a33'\ncanvas.create_line(x+1,y+1,x+tab_width-1,y+1,fill=top,width=1)\ncanvas.create_line(x+1,y+1,x+1,y+22,fill=top,width=1)\ncanvas.create_line(x+1,y+22,x+tab_width-1,y+22,fill=bottom,width=1)\ncanvas.create_line(x+tab_width-1,y+1,x+tab_width-1,y+22,fill=bottom,width=1)\ntab_font=tkfont.Font(root=window.root,family=body,size=10,weight='bold')\ncanvas.create_text(x+tab_width/2,y+11.5,text=fit(tr(tab),tab_width-12,tab_font),fill='#fff3d5' if active or pressed else '#2f1f12',font=tab_font)\n"
METODOS = "def refresh_visual(self):\n    if not self.closed and not self.owner.closing:\n        self.owner.bar_cache=None\n        self.owner.update_horizontal_panel()\n\ndef hover(self,item,value):\n    item['hover']=value\n    if value:\n        self.owner._click_tab_hover=item['tab']\n    elif getattr(self.owner,'_click_tab_hover',None)==item['tab']:\n        self.owner._click_tab_hover=None\n    self.refresh_visual()\n    return 'break'\n\ndef press(self,item):\n    item['pressed']=True\n    self.owner._click_tab_pressed=item['tab']\n    self.refresh_visual()\n    return 'break'\n\ndef release(self,item,event):\n    pressed=item['pressed'];item['pressed']=False\n    self.owner._click_tab_pressed=None\n    canvas=item['canvas']\n    if pressed and 0<=event.x<canvas.winfo_width() and 0<=event.y<canvas.winfo_height():\n        self.owner.panel_tab.set(item['tab'])\n    self.refresh_visual()\n    return 'break'\n\ndef draw(self,item):\n    # A janela pequena recebe apenas o mouse. Todo o desenho fica na tabela.\n    if item.get('key')!='hotspot':\n        item['canvas'].delete('all')\n        item['canvas'].configure(bg='black')\n        item['key']='hotspot'\n"


def corrigir_tabela(codigo):
    tree=ast.parse(codigo);found=False
    for node in ast.walk(tree):
        if isinstance(node,ast.FunctionDef) and node.name=='paint':
            for item in ast.walk(node):
                if isinstance(item,ast.For) and ast.unparse(item.iter)=='enumerate(tabs)':
                    item.body=ast.parse(DESENHO).body
                    found=True
    if not found:raise RuntimeError('Desenho das abas não reconhecido.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def corrigir_cliques(codigo):
    tree=ast.parse(codigo);found=False
    for cls in ast.walk(tree):
        if not isinstance(cls,ast.ClassDef) or cls.name!='ClickTabs':continue
        methods=ast.parse(METODOS).body;names={n.name for n in methods}
        cls.body[:]=[n for n in cls.body if not isinstance(n,ast.FunctionDef) or n.name not in names]
        cls.body.extend(methods)
        alpha=False
        for method in cls.body:
            if not isinstance(method,ast.FunctionDef):continue
            if method.name=='__init__':
                for call in ast.walk(method):
                    if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr=='attributes' and len(call.args)>1 and isinstance(call.args[0],ast.Constant) and call.args[0].value=='-alpha':
                        call.args[1]=ast.Constant(.01);alpha=True
            if method.name=='sync':
                for statement in ast.walk(method):
                    if isinstance(statement,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='opacity' for t in statement.targets):statement.value=ast.Constant(.01)
            if method.name=='hide' and '_click_tab_hover' not in ast.unparse(method):
                method.body[:0]=ast.parse("if getattr(self.owner,'_click_tab_hover',None) is not None or getattr(self.owner,'_click_tab_pressed',None) is not None:\n    self.owner._click_tab_hover=None\n    self.owner._click_tab_pressed=None\n    self.owner.bar_cache=None").body
        if not alpha:raise RuntimeError('Camada clicável não reconhecida.')
        found=True
    if not found:raise RuntimeError('Módulo de abas clicáveis não reconhecido. Aplique primeiro a versão 0.4.0.')
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def main():
    root=Path(__file__).resolve().parent
    changes={}
    for name,fn in (('painel_tabela_036.py',corrigir_tabela),('abas_clicaveis_040.py',corrigir_cliques)):
        path=root/name
        if not path.is_file():raise RuntimeError('Arquivo ausente: '+name+'. Salve este corretor na pasta GeradorMapaAoE2 atualizada até 0.4.0.')
        changes[name]=fn(path.read_text(encoding='utf-8-sig'))
    for name,text in changes.items():ast.parse(text,filename=name)
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    for name in changes:shutil.copy2(root/name,backup/name)
    for name,text in changes.items():(root/name).write_text(text,encoding='utf-8')
    print('Legibilidade e relevo das abas corrigidos. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.4.1, ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
