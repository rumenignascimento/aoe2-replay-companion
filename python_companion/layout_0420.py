"""Reorganiza os widgets existentes; mantém variáveis, callbacks e renderização."""
import tkinter as tk
from tkinter import ttk

CARD='#202424'


def children(widget):
    for child in widget.winfo_children():
        yield child
        yield from children(child)


def text(widget):
    try:return str(widget.cget('text'))
    except tk.TclError:return ''


def relocate(widget,parent,**options):
    if widget.winfo_manager()=='grid':widget.grid_forget()
    elif widget.winfo_manager()=='pack':widget.pack_forget()
    widget.pack(in_=parent,**options)
    widget.lift()


def organize(window):
    if getattr(window,'_layout_0420_ready',False):return
    required=('overview','map_card','preview_canvas','advanced','monitor_label','settings_page')
    if any(not hasattr(window,n) for n in required):return
    overview=window.overview;card=window.map_card;canvas=window.preview_canvas
    original=list(overview.winfo_children())
    tabs=ttk.Notebook(overview,height=150)
    layer_page=ttk.Frame(tabs,style='Card.TFrame',padding=8)
    resource_page=ttk.Frame(tabs,style='Card.TFrame',padding=8)
    advanced_page=ttk.Frame(tabs,style='Card.TFrame',padding=4)
    tabs.add(layer_page,text='Camadas e filtros')
    tabs.add(resource_page,text='Recursos do mapa')
    tabs.add(advanced_page,text='Mais ajustes')
    window._layout_tabs_0420=tabs
    window._layout_advanced_page_0420=advanced_page
    # Reserve bottom controls before the expanding map. The canvas can shrink.
    card.pack_forget()
    tabs.pack(side='bottom',fill='x',pady=(10,0))
    card.pack(fill='both',expand=True)
    canvas.configure(height=90)
    for box in original:
        if box in (card,window.advanced):continue
        labels=[text(w) for w in children(box)]
        is_resource=any('recurso esgotado' in t.lower() or 'restaurar marcadores' in t.lower() for t in labels)
        if is_resource:
            relocate(box,resource_page,fill='both',expand=True)
            # Restore natural request sizes on the former fixed-height toolbar.
            for container in (box,*list(children(box))):
                if isinstance(container,(tk.Frame,ttk.Frame,ttk.LabelFrame)):
                    container.pack_propagate(True)
                if isinstance(container,ttk.Button):
                    container.configure(style='Workspace.Tool.TButton')
                if isinstance(container,(tk.Label,ttk.Label)):
                    try:container.configure(wraplength=480)
                    except tk.TclError:pass
            for row in (box,*list(children(box))):
                buttons=[c for c in row.winfo_children() if isinstance(c,ttk.Button)]
                if len(buttons)<2:continue
                def reflow(event=None,row=row,buttons=buttons):
                    width=row.winfo_width()
                    total=sum(b.winfo_reqwidth()+8 for b in buttons)
                    columns=len(buttons) if width>=total else 2 if width>=max(b.winfo_reqwidth()+8 for b in buttons)*2 else 1
                    if getattr(row,'_layout_cols_0420',None)==columns:return
                    row._layout_cols_0420=columns
                    for b in buttons:
                        if b.winfo_manager()=='pack':b.pack_forget()
                        elif b.winfo_manager()=='grid':b.grid_forget()
                    for index,b in enumerate(buttons):b.grid(row=index//columns,column=index%columns,sticky='ew',padx=3,pady=4)
                    for index in range(len(buttons)):row.columnconfigure(index,weight=1 if index<columns else 0)
                    window.root.after_idle(lambda:resize_tabs(window))
                row.bind('<Configure>',reflow,add='+')
                window.root.after_idle(reflow)
        else:
            switches=[c for c in children(box) if isinstance(c,ttk.Checkbutton)]
            if switches:
                box.pack_forget()
                flat=ttk.Frame(layer_page,style='Card.TFrame')
                flat.pack(fill='both',expand=True)
                clones=[]
                for old in switches:
                    options={key:old.cget(key) for key in ('text','variable','onvalue','offvalue','command','style')}
                    clone=ttk.Checkbutton(flat,**options)
                    if 'disabled' in old.state():clone.state(['disabled'])
                    clones.append(clone)
                def arrange(event=None,flat=flat,clones=clones):
                    width=flat.winfo_width()
                    cols=3 if width>=sum(sorted((c.winfo_reqwidth()+20 for c in clones),reverse=True)[:3]) else 2
                    if getattr(flat,'_cols_0420',None)==cols:return
                    flat._cols_0420=cols
                    for i in range(3):flat.columnconfigure(i,weight=1 if i<cols else 0)
                    for i,c in enumerate(clones):c.grid(row=i//cols,column=i%cols,sticky='w',padx=4,pady=2)
                    window.root.after_idle(lambda:resize_tabs(window))
                flat.bind('<Configure>',arrange,add='+');window.root.after_idle(arrange)
            else:relocate(box,layer_page,fill='both',expand=True)
    # Advanced options remain provided by the original navigate() callback.
    relocate(window.advanced,advanced_page,fill='both',expand=True)
    window.advanced.pack_propagate(True)
    # Hide the long icon sliders until the user opens Map adjustments.
    toolbars=[getattr(window,n,None) for n in ('_orientation_toolbar_042','_icon_sizes_toolbar_043')]
    toolbars=[w for w in toolbars if w is not None and w.winfo_exists()]
    if toolbars:
        tools=ttk.Frame(card,style='Card.TFrame',padding=(10,6))
        for widget in toolbars:relocate(widget,tools,fill='x',pady=3)
        heading=next((w for w in card.winfo_children() if any(isinstance(c,ttk.Combobox) for c in w.winfo_children())),None)
        if heading is not None:
            window._layout_tools_open_0420=False
            def toggle():
                opened=not window._layout_tools_open_0420
                window._layout_tools_open_0420=opened
                if opened:tools.pack(fill='x',before=canvas)
                else:tools.pack_forget()
                button.configure(text='Fechar ajustes' if opened else 'Ajustar mapa')
                window.preview_key=None
            button=ttk.Button(heading,text='Ajustar mapa',command=toggle,style='Workspace.Tool.TButton')
            button.pack(side='right',padx=12)
            window._layout_tools_button_0420=button
    # Fixed actions live outside the scrolled overlay settings.
    right=next((w for w in children(window.monitor_label.master.master)
                if any(isinstance(c,(tk.Label,ttk.Label)) and text(c)=='Overlay' for c in w.winfo_children())),None)
    if right is not None:
        action_methods={'Testar por 10 segundos':getattr(window,'preview_position_target',None),
                        'Celular / tablet · QR Code':getattr(window,'mobile_dialog',None),
                        'Salvar configurações':getattr(window,'save_settings',None)}
        old=list(children(right))
        for widget in old:
            if isinstance(widget,ttk.Button) and text(widget) in action_methods:widget.pack_forget()
        actions=ttk.Frame(right,style='Card.TFrame',padding=10)
        right_children=right.pack_slaves()
        scroll=next((w for w in right_children if isinstance(w,ttk.Frame)),None)
        options={'side':'bottom','fill':'x'}
        if scroll is not None:options['before']=scroll
        actions.pack(**options)
        for label,callback in action_methods.items():
            if callable(callback):
                ttk.Button(actions,text=label,command=callback,style='Test.TButton' if label.startswith('Testar') else 'Workspace.Tool.TButton').pack(fill='x',pady=3)
    # Avoid the former oversized button paddings consuming the resource toolbar.
    style=ttk.Style(window.root)
    style.configure('Workspace.Tool.TButton',padding=(10,7))
    # Small notebook area follows the selected page's needs; scroll advanced controls.
    def fit(event=None):
        window.root.after_idle(lambda:resize_tabs(window))
    tabs.bind('<<NotebookTabChanged>>',fit,add='+')
    top=window.monitor_label.master
    title=next((w for w in top.winfo_children() if text(w)=='AoE II · Replay Companion'),None)
    def responsive(event=None):
        if event is not None and event.widget is not window.root:return
        compact=window.root.winfo_width()<1250
        if title is not None:title.configure(text='Replay Companion' if compact else 'AoE II · Replay Companion',font=(window.title_font,16 if compact else 19,'bold'))
        heading=next((w for w in card.winfo_children() if any(isinstance(c,ttk.Combobox) for c in w.winfo_children())),None)
        if heading is not None:
            for widget in heading.winfo_children():
                if isinstance(widget,tk.Label):widget.configure(text='Minimapa' if compact else 'Prévia do minimapa',font=(window.title_font,14 if compact else 16,'bold'))
                if isinstance(widget,ttk.Combobox):widget.configure(width=10 if compact else 17)
        if compact:window.monitor_label.pack_forget()
        elif not window.monitor_label.winfo_manager():window.monitor_label.pack(side='right',padx=12)
        resize_tabs(window)
    window.root.bind('<Configure>',responsive,add='+')
    window._layout_0420_ready=True
    responsive()
    fit()


def resize_tabs(window):
    tabs=window._layout_tabs_0420
    if not tabs.winfo_exists():return
    page=tabs.nametowidget(tabs.select())
    height=max(110,min(190,page.winfo_reqheight()+12))
    # The lower area must not claim the entire short window.
    height=min(height,max(110,round(window.root.winfo_height()*.24)))
    tabs.configure(height=height)
    window.preview_key=None


def ativar(g):
    if g.get('_layout_0420_active'):return
    g['_layout_0420_active']=True
    Base=g['Window']
    class Window(Base):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.root.after_idle(lambda:organize(self))
        def navigate(self,name):
            result=super().navigate(name)
            if getattr(self,'_layout_0420_ready',False):
                relocate(self.advanced,self._layout_advanced_page_0420,fill='both',expand=True)
                self.advanced.pack_propagate(True)
                if name in ('Overlay','Minimapa'):
                    self._layout_tabs_0420.select(self._layout_advanced_page_0420)
                self.root.after_idle(lambda:resize_tabs(self))
            return result
    g['Window']=Window
