import ast
import shutil
from datetime import datetime
from pathlib import Path

CONTROLES = "def _tamanhos_icones_043(window):\n    import tkinter as tk\n    from tkinter import ttk\n    existing=getattr(window,'_icon_sizes_toolbar_043',None)\n    if existing is not None and existing.winfo_exists():\n        return\n    canvas=window.preview_canvas\n    box=ttk.Frame(canvas.master,style='Card.TFrame')\n    box.pack(fill='x',before=canvas,padx=10,pady=(0,8))\n    window._icon_sizes_toolbar_043=box\n    window._icon_size_scales_043={}\n    window._icon_size_values_043={}\n    window._icon_size_fields_043={}\n    traces=[];cells=[]\n    items=(('Gaia','gaia_icon_size',6,48,'gaia_options'),\n           ('Construções','central_icon_size',6,48,'central_layers'),\n           ('Unidades','troops_icon_size',10,40,'troop_options'))\n    def update(callback):\n        function=getattr(window,callback,None)\n        if function is not None:\n            function()\n        window.next_frame=0\n        if hasattr(window,'refresh_central'):\n            window.refresh_central()\n    for label,name,low,high,callback in items:\n        cell=ttk.Frame(box,style='Card.TFrame');cells.append(cell)\n        cell.columnconfigure(1,weight=1)\n        source=getattr(window,name)\n        value=tk.DoubleVar(master=window.root,value=max(low,min(high,int(source.get()))))\n        guard=[False]\n        def from_field(*args,src=source,val=value,lock=guard,lo=low,hi=high,cb=callback):\n            if lock[0]:return\n            try:number=int(src.get())\n            except (ValueError,tk.TclError):return\n            if not lo<=number<=hi:return\n            lock[0]=True\n            try:val.set(number)\n            finally:lock[0]=False\n            update(cb)\n        def from_slider(raw,src=source,val=value,lock=guard,lo=low,hi=high,cb=callback):\n            if lock[0]:return\n            number=max(lo,min(hi,round(float(raw))))\n            lock[0]=True\n            try:\n                src.set(number);val.set(number)\n            finally:lock[0]=False\n            update(cb)\n        ttk.Label(cell,text=label).grid(row=0,column=0,sticky='w',padx=(0,5))\n        field=ttk.Spinbox(cell,textvariable=source,from_=low,to=high,increment=1,width=4)\n        field.grid(row=0,column=1,sticky='ew')\n        slider=ttk.Scale(cell,from_=low,to=high,variable=value,command=from_slider)\n        slider.grid(row=1,column=0,columnspan=2,sticky='ew',pady=(4,0))\n        window._icon_size_scales_043[name]=slider\n        window._icon_size_values_043[name]=value\n        window._icon_size_fields_043[name]=field\n        traces.append((source,source.trace_add('write',from_field)))\n    layout=[None]\n    def reflow(event=None):\n        needed=max(cell.winfo_reqwidth()+12 for cell in cells)*len(cells)\n        columns=3 if box.winfo_width()>=needed else 1\n        if columns==layout[0]:return\n        layout[0]=columns\n        for column in range(3):box.columnconfigure(column,weight=1 if column<columns else 0,uniform='icon043' if column<columns else '')\n        for index,cell in enumerate(cells):cell.grid(row=index//columns,column=index%columns,sticky='ew',padx=(0,10) if columns==3 and index<2 else 0,pady=(0,5))\n    box.bind('<Configure>',reflow,add='+')\n    window.root.after_idle(reflow)\n    def cleanup(event):\n        if event.widget is box:\n            for variable,token in traces:\n                try:variable.trace_remove('write',token)\n                except tk.TclError:pass\n    box.bind('<Destroy>',cleanup,add='+')\n"
ESTADO = "icon_size=[int(t.OPTIONS[3])]\nimport threading\nsize_context=threading.local()\nold_validate_sizes=g['p']._validate_config\n\ndef validate_sizes(values):\n    if isinstance(values,dict):\n        values=dict(values)\n        value=values.get('gaia_icon_size',values.get('troops_icon_size',int(t.OPTIONS[3])))\n        if isinstance(value,str):\n            try:value=int(value)\n            except ValueError:pass\n        values['gaia_icon_size']=value\n    result=old_validate_sizes(values)\n    value=result['gaia_icon_size']\n    if isinstance(value,bool) or not isinstance(value,int) or not 6<=value<=48:\n        raise ValueError('Ícones Gaia: use um inteiro entre 6 e 48.')\n    return result\ng['p']._validate_config=validate_sizes\n"
JOB = "def job(self,*args,**kwargs):\n    previous=getattr(size_context,'value',None)\n    size_context.value=icon_size[0]\n    try:\n        return super().job(*args,**kwargs)\n    finally:\n        if previous is None:\n            del size_context.value\n        else:\n            size_context.value=previous\n"


def adaptar_central(codigo):
    tree=ast.parse(codigo);found=False
    for node in ast.walk(tree):
        if not isinstance(node,ast.FunctionDef):continue
        if node.name=='build_central':
            if '_tamanhos_icones_043' not in ast.unparse(node):node.body.extend(ast.parse('_tamanhos_icones_043(self)').body)
            found=True
        if node.name=='navigate':
            class Limpar(ast.NodeTransformer):
                def visit_Expr(self,statement):
                    call=statement.value
                    if isinstance(call,ast.Call) and ast.unparse(call.func)=='self.field' and len(call.args)>2 and ast.unparse(call.args[2]) in ('self.central_icon_size','self.troops_icon_size'):
                        return None
                    return self.generic_visit(statement)
                def visit_If(self,statement):
                    self.generic_visit(statement)
                    if not statement.body:statement.body=[ast.Pass()]
                    return statement
            Limpar().visit(node)
    if not found:raise RuntimeError('Central de replay não reconhecida.')
    tree.body[:]=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='_tamanhos_icones_043']
    tree.body.extend(ast.parse(CONTROLES).body)
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def adaptar_gaia(codigo):
    tree=ast.parse(codigo)
    if not any(isinstance(n,ast.Import) and any(a.name=='tkinter' and a.asname=='tk' for a in n.names) for n in tree.body):
        tree.body.insert(0,ast.parse('import tkinter as tk').body[0])
    activate=next((n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='ativar'),None)
    if activate is None:raise RuntimeError('Módulo Gaia não reconhecido.')
    if 'validate_sizes' not in ast.unparse(activate):
        found=False
        for call in ast.walk(activate):
            if isinstance(call,ast.Call) and ast.unparse(call.func)=="g['p'].CONFIG_DEFAULTS.update":
                call.keywords.append(ast.keyword(arg='gaia_icon_size',value=ast.parse('int(t.OPTIONS[3])',mode='eval').body));found=True
        if not found:raise RuntimeError('Configurações Gaia não reconhecidas.')
        index=next((i for i,n in enumerate(activate.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='visible' for t in n.targets)),None)
        if index is None:raise RuntimeError('Estado Gaia não reconhecido.')
        activate.body[index+1:index+1]=ast.parse(ESTADO).body
    render=next((n for n in activate.body if isinstance(n,ast.FunctionDef) and n.name=='render'),None)
    if render is None:raise RuntimeError('Renderização Gaia não reconhecida.')
    found=False
    for node in ast.walk(render):
        if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='size' for t in node.targets):
            if ast.unparse(node.value) not in ("t.OPTIONS[3]","getattr(size_context, 'value', icon_size[0])"):
                raise RuntimeError('Origem do tamanho Gaia diferente do esperado.')
            node.value=ast.parse("getattr(size_context,'value',icon_size[0])",mode='eval').body;found=True
    if not found:raise RuntimeError('Tamanho Gaia não reconhecido.')
    cls=next((n for n in activate.body if isinstance(n,ast.ClassDef) and n.name=='Window'),None)
    if cls is None:raise RuntimeError('Janela Gaia não reconhecida.')
    setup=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='setup_position_controls')
    if 'gaia_icon_size' not in ast.unparse(setup):
        setup.body.extend(ast.parse("self.gaia_icon_size=tk.IntVar(value=g['p'].CONFIG_DEFAULTS['gaia_icon_size'])\nself.gaia_icon_size.trace_add('write',self.gaia_options)").body)
    options=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='gaia_options')
    if 'gaia_icon_size' not in ast.unparse(options):
        options.body.extend(ast.parse("try:\n    size=int(self.gaia_icon_size.get())\n    if 6<=size<=48: icon_size[0]=size\nexcept (ValueError,tk.TclError):\n    pass").body)
    previous=next((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='job'),None)
    if previous is not None and 'size_context' not in ast.unparse(previous):raise RuntimeError('A janela Gaia contém um job personalizado; integração não aplicada.')
    cls.body[:]=[n for n in cls.body if not isinstance(n,ast.FunctionDef) or n.name!='job']
    cls.body.extend(ast.parse(JOB).body)
    ast.fix_missing_locations(tree);return ast.unparse(tree)+'\n'


def main():
    root=Path(__file__).resolve().parent
    changes={}
    for name,fn in (('central_replay.py',adaptar_central),('gaia_minimapa.py',adaptar_gaia)):
        path=root/name
        if not path.is_file():raise RuntimeError('Arquivo ausente: '+name+'. Salve este atualizador na pasta GeradorMapaAoE2.')
        changes[name]=fn(path.read_text(encoding='utf-8-sig'))
    for name,text in changes.items():ast.parse(text,filename=name)
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    for name in changes:shutil.copy2(root/name,backup/name)
    for name,text in changes.items():(root/name).write_text(text,encoding='utf-8')
    print('Tamanho independente de Gaia, construções e unidades adicionado. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.4.3, ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
