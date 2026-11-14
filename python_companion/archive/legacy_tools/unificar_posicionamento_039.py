import ast
import shutil
from pathlib import Path
from datetime import datetime

METODOS = "def setup_table_position_controls(self, parent):\n    box = ttk.Frame(parent, style='Card.TFrame')\n    box.pack(fill='x')\n    traces = []\n    if not hasattr(self,'_table_axis_sliders'):\n        self._table_axis_sliders = {}\n        self._table_axis_vars = {}\n    self.switch(box,'Exibir painel horizontal',self.caption_show)\n    self.field(box,'Posição',self.caption_corner,values=('Superior esquerdo','Superior direito','Inferior esquerdo','Inferior direito'))\n    def move():\n        if not self.closing:\n            self.update_horizontal_panel()\n    for axis in ('x','y'):\n        source = getattr(self,'caption_'+axis)\n        self.field(box,'Eixo '+axis.upper()+' (px)',source,bounds=(0,10000))\n        limit = self.root.winfo_screenwidth() if axis=='x' else self.root.winfo_screenheight()\n        try:\n            initial = int(source.get())\n        except (ValueError,tk.TclError):\n            initial = 0\n        value = tk.DoubleVar(master=self.root,value=max(0,min(limit,initial)))\n        guard = [False]\n        def from_field(*args,src=source,val=value,cap=limit,lock=guard):\n            if lock[0]:\n                return\n            try:\n                number = int(src.get())\n            except (ValueError,tk.TclError):\n                return\n            lock[0] = True\n            try:\n                val.set(max(0,min(cap,number)))\n            finally:\n                lock[0] = False\n            self.root.after_idle(move)\n        def from_slider(raw,src=source,val=value,cap=limit,lock=guard):\n            if lock[0]:\n                return\n            lock[0] = True\n            try:\n                number = max(0,min(cap,round(float(raw))))\n                src.set(str(number));val.set(number)\n            finally:\n                lock[0] = False\n            self.root.after_idle(move)\n        slider = ttk.Scale(box,from_=0,to=max(1,limit),variable=value,command=from_slider)\n        slider.pack(fill='x',pady=(0,8))\n        self._table_axis_sliders[axis] = slider\n        self._table_axis_vars[axis] = value\n        traces.append((source,source.trace_add('write',from_field)))\n    self.field(box,'Largura do painel (px)',self.panel_width,bounds=(300,3600))\n    self.field(box,'Altura máxima (px)',self.table_calibration_height,bounds=(0,10000))\n    ttk.Button(box,text='Calibrar área da tabela · 5s',command=self.calibrate_table).pack(fill='x',pady=8)\n    ttk.Label(box,text='X/Y partem do canto escolhido.\\nAltura 0 = automática; o painel usa páginas quando necessário.\\nCalibrar: volte ao jogo em até 5s e selecione a área. Esc cancela.\\nA mesma posição vale para Militar e Economia.',wraplength=210).pack(anchor='w',pady=5)\n    def cleanup(event):\n        if event.widget is box:\n            for variable,token in traces:\n                try:\n                    variable.trace_remove('write',token)\n                except tk.TclError:\n                    pass\n    box.bind('<Destroy>',cleanup,add='+')\n\n\ndef preview_position_target(self):\n    outer = getattr(self,'overlay_settings_tabs',None)\n    inner = getattr(self,'position_target_tabs',None)\n    table_page = getattr(self,'position_panel_page',None)\n    position_page = getattr(self,'overlay_position_page',None)\n    if outer is not None and inner is not None and outer.select()==str(position_page) and inner.select()==str(table_page):\n        self.caption_show.set(True)\n        self.preview_until = g['time'].monotonic()+10\n        self.bar_cache = None\n        self.update_horizontal_panel()\n        return\n    self.preview()\n\n\ndef fit_position_notebooks(self, event=None):\n    if getattr(self,'_position_layout_pending',False):\n        return\n    self._position_layout_pending = True\n    def fit_inner():\n        if self.closing:\n            return\n        notebook = self.position_target_tabs\n        page = notebook.nametowidget(notebook.select())\n        notebook.configure(height=max(1,page.winfo_reqheight()))\n        self.root.after_idle(fit_outer)\n    def fit_outer():\n        self._position_layout_pending = False\n        if self.closing:\n            return\n        notebook = self.overlay_settings_tabs\n        page = notebook.nametowidget(notebook.select())\n        notebook.configure(height=max(1,page.winfo_reqheight()))\n    self.root.after_idle(fit_inner)\n"
PAGES = "self.overlay_settings_tabs = tabs\nself.overlay_position_page = position\nposition_targets = ttk.Notebook(position)\nposition_targets.pack(fill='x', expand=True)\nmap_position = ttk.Frame(position_targets, style='Card.TFrame', padding=6)\npanel_position = ttk.Frame(position_targets, style='Card.TFrame', padding=6)\nposition_targets.add(map_position, text='Minimapa')\nposition_targets.add(panel_position, text='Painel horizontal')\nself.position_target_tabs = position_targets\nself.position_minimap_page = map_position\nself.position_panel_page = panel_position\nself.setup_table_position_controls(panel_position)\nposition_targets.bind('<<NotebookTabChanged>>', self.fit_position_notebooks, add='+')\ntabs.bind('<<NotebookTabChanged>>', self.fit_position_notebooks, add='+')\nself.fit_position_notebooks()\n"


def adaptar_central(codigo):
    tree=ast.parse(codigo);found=False
    for node in ast.walk(tree):
        if not isinstance(node,ast.FunctionDef):
            continue
        if node.name=='build_central':
            if 'position_target_tabs' not in ast.unparse(node):
                index=next((i for i,n in enumerate(node.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='self.field' and len(n.value.args)>0 and isinstance(n.value.args[0],ast.Name) and n.value.args[0].id=='position'),None)
                if index is None:
                    raise RuntimeError('Aba Posição não reconhecida.')
                for call in ast.walk(node):
                    if isinstance(call,ast.Call) and ast.unparse(call.func) in ('self.field','self.add_position_slider','self.setup_minimap_fit_controls'):
                        for arg in call.args:
                            if isinstance(arg,ast.Name) and arg.id=='position':arg.id='map_position'
                node.body[index:index]=ast.parse(PAGES).body
            for call in ast.walk(node):
                if isinstance(call,ast.Call) and ast.unparse(call.func)=='ttk.Button':
                    text=next((k.value.value for k in call.keywords if k.arg=='text' and isinstance(k.value,ast.Constant)),None)
                    if isinstance(text,str) and text.startswith('Testar por 10'):
                        command=next((k for k in call.keywords if k.arg=='command'),None)
                        if command:command.value=ast.Attribute(value=ast.Name(id='self',ctx=ast.Load()),attr='preview_position_target',ctx=ast.Load())
            found=True
        if node.name=='navigate':
            class Clean(ast.NodeTransformer):
                def visit_Expr(self,statement):
                    call=statement.value
                    if isinstance(call,ast.Call) and ast.unparse(call.func)=='self.field' and len(call.args)>2 and ast.unparse(call.args[2]) in ('self.caption_corner','self.caption_x','self.caption_y'):
                        return None
                    return self.generic_visit(statement)
            Clean().visit(node)
    if not found:
        raise RuntimeError('Central não reconhecida.')
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def adaptar_horizontal(codigo):
    tree=ast.parse(codigo);found=False
    for cls in ast.walk(tree):
        if not isinstance(cls,ast.ClassDef) or cls.name!='Window':
            continue
        setup=next((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='setup_horizontal_controls'),None)
        if setup is None:
            continue
        if not {'setup_table_position_controls','calibrate_table','table_height_limit'}.issubset({n.name for n in cls.body if isinstance(n,ast.FunctionDef)}):
            raise RuntimeError('Aplique primeiro a atualização 0.3.8 de posição e calibração da tabela.')
        methods=ast.parse(METODOS).body;names={n.name for n in methods}
        cls.body[:]=[n for n in cls.body if not isinstance(n,ast.FunctionDef) or n.name not in names]
        cls.body.extend(methods)
        setup.body[:]=[n for n in setup.body if not (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and (ast.unparse(n.value.func)=='self.setup_table_position_controls' or (ast.unparse(n.value.func)=='self.field' and len(n.value.args)>2 and ast.unparse(n.value.args[2])=='self.panel_width')))]
        found=True
    if not found:
        raise RuntimeError('Painel horizontal não reconhecido.')
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def main():
    root=Path(__file__).resolve().parent
    changes={}
    for name,fn in (('central_replay.py',adaptar_central),('painel_horizontal.py',adaptar_horizontal)):
        path=root/name
        if not path.is_file():
            raise RuntimeError('Salve este atualizador na pasta completa GeradorMapaAoE2. Ausente: '+name)
        changes[name]=fn(path.read_text(encoding='utf-8-sig'))
    for name,text in changes.items():ast.parse(text,filename=name)
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');backup.mkdir(parents=True)
    for name in changes:shutil.copy2(root/name,backup/name)
    for name,text in changes.items():(root/name).write_text(text,encoding='utf-8')
    print('Posicionamento unificado: Minimapa / Painel horizontal. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.3.9, ou superior à última gerada.')


if __name__=='__main__':
    try:main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
