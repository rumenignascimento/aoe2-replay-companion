import ast
import shutil
from pathlib import Path
from datetime import datetime

METODO = "def setup_table_position_controls(self, parent):\n    box = ttk.LabelFrame(parent, text='Posição da tabela · Militar e Economia', padding=8)\n    box.pack(fill='x', pady=8)\n    box.columnconfigure(0, weight=1)\n    box.columnconfigure(1, weight=1)\n    ttk.Label(box, text='Posição').grid(row=0, column=0, sticky='w', padx=4)\n    ttk.Combobox(box, textvariable=self.caption_corner, state='readonly',\n                 values=('Superior esquerdo','Superior direito','Inferior esquerdo','Inferior direito')).grid(row=0, column=1, sticky='ew', padx=4, pady=4)\n    traces = []\n    if not hasattr(self, '_table_axis_sliders'):\n        self._table_axis_sliders = {}\n        self._table_axis_vars = {}\n    def move():\n        if not self.closing:\n            self.update_horizontal_panel()\n    for column, axis in enumerate(('x','y')):\n        panel = ttk.Frame(box)\n        panel.grid(row=1, column=column, sticky='ew', padx=4, pady=4)\n        panel.columnconfigure(1, weight=1)\n        source = getattr(self, 'caption_' + axis)\n        limit = self.root.winfo_screenwidth() if axis=='x' else self.root.winfo_screenheight()\n        try:\n            initial = int(source.get())\n        except (ValueError, tk.TclError):\n            initial = 0\n        value = tk.DoubleVar(master=self.root, value=max(0,min(limit,initial)))\n        guard = [False]\n        def from_field(*args, src=source, val=value, cap=limit, lock=guard):\n            if lock[0]:\n                return\n            try:\n                number = int(src.get())\n            except (ValueError, tk.TclError):\n                return\n            lock[0] = True\n            try:\n                val.set(max(0,min(cap,number)))\n            finally:\n                lock[0] = False\n            self.root.after_idle(move)\n        def from_slider(raw, src=source, val=value, cap=limit, lock=guard):\n            if lock[0]:\n                return\n            lock[0] = True\n            try:\n                number = max(0,min(cap,round(float(raw))))\n                src.set(str(number))\n                val.set(number)\n            finally:\n                lock[0] = False\n            self.root.after_idle(move)\n        ttk.Label(panel, text='Eixo '+axis.upper()+' (px)').grid(row=0,column=0,sticky='w',padx=(0,6))\n        ttk.Spinbox(panel, textvariable=source, from_=0, to=10000, increment=1, width=8).grid(row=0,column=1,sticky='ew')\n        slider = ttk.Scale(panel, from_=0, to=max(1,limit), variable=value, command=from_slider)\n        slider.grid(row=1,column=0,columnspan=2,sticky='ew',pady=5)\n        self._table_axis_sliders[axis] = slider\n        self._table_axis_vars[axis] = value\n        traces.append((source,source.trace_add('write',from_field)))\n    row = ttk.Frame(box)\n    ttk.Label(box,text='Altura máxima (px; 0 = automática)').grid(row=2,column=0,sticky='w',padx=4,pady=4)\n    ttk.Spinbox(box,textvariable=self.table_calibration_height,from_=0,to=10000,increment=1,width=8).grid(row=2,column=1,sticky='ew',padx=4)\n    ttk.Button(box,text='Calibrar área da tabela · 5s',command=self.calibrate_table).grid(row=3,column=0,columnspan=2,sticky='ew',padx=4,pady=5)\n    row.grid(row=4,column=0,columnspan=2,sticky='ew',pady=5)\n    def preview_table():\n        self.caption_show.set(True)\n        self.preview()\n    ttk.Button(row,text='Testar por 10 segundos',command=preview_table).pack(side='left',padx=4)\n    ttk.Button(row,text='Salvar configurações',command=self.save_settings).pack(side='left',padx=4)\n    ttk.Label(box,text='X: deslocamento horizontal. Y: deslocamento vertical.\\nCalibrar: volte ao jogo em até 5s e selecione a área. Esc cancela.\\nA posição vale para ambas as abas; a altura é um limite, sem esticar os ícones.',wraplength=500).grid(row=5,column=0,columnspan=2,sticky='w',padx=4)\n    def cleanup(event):\n        if event.widget is box:\n            for variable, token in traces:\n                try:\n                    variable.trace_remove('write',token)\n                except tk.TclError:\n                    pass\n    box.bind('<Destroy>',cleanup,add='+')\n\n\ndef table_height_limit(self, automatic):\n    try:\n        value = int(self.table_calibration_height.get())\n    except (ValueError,tk.TclError):\n        return automatic\n    if value < 130:\n        return automatic\n    area = self.native.game()\n    available = area[3] if area else self.root.winfo_screenheight()\n    return max(130, min(value, max(130, available-16)))\n\n\ndef calibrate_table(self):\n    if self._table_calibrating or getattr(self,'_fit_calibrating',False):\n        return\n    self._table_calibrating = True\n    old_show = self.show.get()\n    old_caption = self.caption_show.get()\n    self.show.set(False)\n    self.caption_show.set(False)\n    self.overlay.withdraw()\n    self.caption.withdraw()\n    self.root.withdraw()\n    def finish():\n        self._table_calibrating = False\n        self.show.set(old_show)\n        self.caption_show.set(old_caption)\n        self.root.deiconify()\n        self.root.lift()\n    def select():\n        if self.closing:\n            return\n        area = self.native.game()\n        if not area:\n            finish()\n            self.status.set('Calibração cancelada: volte ao Age of Empires II DE em até cinco segundos.')\n            return\n        x, y, width, height = area\n        popup = tk.Toplevel(self.root)\n        popup.overrideredirect(True)\n        popup.attributes('-topmost',True)\n        popup.attributes('-alpha',.30)\n        popup.geometry(f'{width}x{height}{x:+d}{y:+d}')\n        canvas = tk.Canvas(popup,bg='black',highlightthickness=0,cursor='crosshair')\n        canvas.pack(fill='both',expand=True)\n        instruction = canvas.create_text(width//2,35,text='Selecione a área da tabela. Mínimo: 300 × 130 pixels. Esc cancela.',fill='white',font=('Segoe UI',13,'bold'))\n        start = []\n        marker = [None]\n        def close():\n            popup.destroy()\n            finish()\n        def press(event):\n            start[:] = [max(0,min(width,event.x)),max(0,min(height,event.y))]\n        def bounds(event):\n            return sorted((start[0],max(0,min(width,event.x))))+sorted((start[1],max(0,min(height,event.y))))\n        def drag(event):\n            if not start:\n                return\n            left,right,top,bottom = bounds(event)\n            if marker[0] is not None:\n                canvas.delete(marker[0])\n            marker[0] = canvas.create_rectangle(left,top,right,bottom,outline='#ffcf71',width=4)\n        def release(event):\n            if not start:\n                return\n            left,right,top,bottom = bounds(event)\n            if right-left < 300 or right-left > 3600 or bottom-top < 130:\n                canvas.itemconfigure(instruction,text='Selecione largura entre 300 e 3600 px e altura de pelo menos 130 px. Esc cancela.')\n                return\n            self.caption_corner.set('Superior esquerdo')\n            self.caption_x.set(str(left))\n            self.caption_y.set(str(top))\n            self.panel_width.set(right-left)\n            self.table_calibration_height.set(bottom-top)\n            close()\n            self.caption_show.set(True)\n            self.preview_until = g['time'].monotonic()+10\n            self.bar_cache = None\n            self.update_horizontal_panel()\n            self.save_settings()\n        canvas.bind('<ButtonPress-1>',press)\n        canvas.bind('<B1-Motion>',drag)\n        canvas.bind('<ButtonRelease-1>',release)\n        popup.bind('<Escape>',lambda event:close())\n        popup.update_idletasks()\n        hwnd = self.native.u.GetAncestor(popup.winfo_id(),2)\n        self.native.u.SetWindowPos(hwnd,None,x,y,width,height,0x14)\n        popup.focus_force()\n    self.root.after(5000,select)\n"


def adaptar(codigo):
    tree=ast.parse(codigo);found=set()
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and ast.unparse(node.func)=="g['p'].CONFIG_DEFAULTS.update":
            if any(k.arg=='panel_width' for k in node.keywords):
                if not any(k.arg=='table_calibration_height' for k in node.keywords):
                    node.keywords.append(ast.keyword(arg='table_calibration_height',value=ast.Constant(0)))
                found.add('defaults')
        if isinstance(node,ast.FunctionDef) and node.name=='validate' and 'panel_width' in ast.unparse(node):
            if 'table_calibration_height' not in ast.unparse(node):
                index=next(i for i,n in enumerate(node.body) if isinstance(n,ast.Return))
                node.body[index:index]=ast.parse("height=result['table_calibration_height']\nif isinstance(height,bool) or not isinstance(height,int) or (height != 0 and not 130 <= height <= 10000): raise ValueError('Altura da tabela: use 0 (automática) ou um inteiro entre 130 e 10000.')").body
            found.add('validate')
    for cls in ast.walk(tree):
        if not isinstance(cls,ast.ClassDef) or cls.name!='Window':
            continue
        setup=next((n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='setup_horizontal_controls'),None)
        if setup is None:
            continue
        methods=ast.parse(METODO).body;names={n.name for n in methods}
        cls.body[:]=[n for n in cls.body if not isinstance(n,ast.FunctionDef) or n.name not in names]
        cls.body.extend(methods)
        init=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='__init__')
        if 'table_calibration_height' not in ast.unparse(init):
            init.body[:0]=ast.parse('self.table_calibration_height=tk.IntVar(master=root,value=0)\nself._table_calibrating=False').body
        update=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='update_horizontal_panel')
        if 'table_height_limit' not in ast.unparse(update):
            index=next((i for i,n in enumerate(update.body) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='max_height' for t in n.targets)),None)
            if index is None:
                raise RuntimeError('Limite de altura não reconhecido.')
            update.body[index+1:index+1]=ast.parse('max_height=self.table_height_limit(max_height)').body
        if 'setup_table_position_controls' not in ast.unparse(setup):
            index=next((i for i,n in enumerate(setup.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and ast.unparse(n.value.func)=='self.field' and len(n.value.args)>1 and isinstance(n.value.args[1],ast.Constant) and n.value.args[1].value=='Largura do painel (px)'),None)
            if index is None:
                raise RuntimeError('Controles do painel não reconhecidos.')
            setup.body[index+1:index+1]=ast.parse('self.setup_table_position_controls(box)').body
        found.add('controls')
    if found!={'defaults','validate','controls'}:
        raise RuntimeError('Módulo do painel horizontal diferente do esperado: '+str(found))
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'


def main():
    root=Path(__file__).resolve().parent
    path=root/'painel_horizontal.py'
    if not path.is_file():
        raise RuntimeError('Salve este atualizador na pasta GeradorMapaAoE2, junto de painel_horizontal.py.')
    codigo=adaptar(path.read_text(encoding='utf-8-sig'))
    ast.parse(codigo)
    backup=root/'backups_atualizacoes'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup.mkdir(parents=True)
    shutil.copy2(path,backup/path.name)
    path.write_text(codigo,encoding='utf-8')
    print('Posicionamento X/Y e calibração da tabela adicionados. Backup:',backup)
    print('Execute py -3.12 gerar_atualizacao.py. Versão sugerida: 0.3.8, ou superior à última gerada.')


if __name__=='__main__':
    try:
        main()
    except Exception as erro:
        print('ERRO:',erro)
        raise SystemExit(1)
