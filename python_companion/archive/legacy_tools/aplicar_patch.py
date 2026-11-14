from pathlib import Path
import os,threading,queue,argparse
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from patch_core import apply_patch,rollback

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--instalacao')
    parser.add_argument('--patch')
    args=parser.parse_args()
    root=tk.Tk();root.title('Atualizador · AoE II Replay Companion');root.geometry('690x350')
    folder=tk.StringVar(value=str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'Programs/AoE2Overlay'))
    if args.instalacao:folder.set(os.path.expandvars(args.instalacao))
    patch=tk.StringVar(value=args.patch or '');status=tk.StringVar(value='Feche o AoE II Replay Companion antes de aplicar ou restaurar um patch.')
    box=ttk.Frame(root,padding=20);box.pack(fill='both',expand=True)
    ttk.Label(box,text='Atualização por patch',font=('Segoe UI',17,'bold')).pack(anchor='w',pady=(0,16))
    ttk.Label(box,text='Pasta onde está AoE2Overlay.exe').pack(anchor='w')
    ttk.Entry(box,textvariable=folder).pack(fill='x')
    ttk.Button(box,text='Escolher instalação…',command=lambda:choose_dir()).pack(anchor='w',pady=4)
    ttk.Label(box,text='Arquivo .aoe2patch').pack(anchor='w')
    ttk.Entry(box,textvariable=patch).pack(fill='x')
    ttk.Button(box,text='Abrir patch…',command=lambda:choose_patch()).pack(anchor='w',pady=4)
    buttons=ttk.Frame(box);buttons.pack(fill='x',pady=12)
    events=queue.Queue();busy=[False]
    def choose_dir():
        p=filedialog.askdirectory(parent=root,initialdir=folder.get())
        if p:folder.set(p)
    def choose_patch():
        p=filedialog.askopenfilename(parent=root,filetypes=[('Patch AoE II','*.aoe2patch'),('ZIP','*.zip')])
        if p:patch.set(p)
    def run(undo=False):
        if busy[0]:return
        if not undo and not Path(patch.get()).is_file():messagebox.showerror('Patch','Escolha um arquivo de patch.',parent=root);return
        if not messagebox.askyesno('Atualização','O Companion está fechado? Continuar com '+('a restauração?' if undo else 'a atualização?'),parent=root):return
        target=os.path.expanduser(os.path.expandvars(folder.get().strip()));package=os.path.expanduser(os.path.expandvars(patch.get().strip()));busy[0]=True
        apply.config(state='disabled');restore.config(state='disabled');status.set('Verificando arquivos e executando operação…')
        def work():
            try:
                result=rollback(target) if undo else apply_patch(package,target)
                events.put((True,'Versão restaurada: '+result['base_version'] if undo else 'Atualizado para '+result['version']+'. Abra o Companion normalmente.'))
            except Exception as e:events.put((False,str(e)+'\nSe houver arquivo em uso, feche o Companion e tente novamente.'))
        threading.Thread(target=work,daemon=True).start()
    def poll():
        if not events.empty():
            ok,msg=events.get();busy[0]=False;apply.config(state='normal');restore.config(state='normal');status.set(msg)
            (messagebox.showinfo if ok else messagebox.showerror)('Atualizador',msg,parent=root)
        root.after(100,poll)
    apply=ttk.Button(buttons,text='Aplicar patch',command=run);apply.pack(side='left',padx=(0,8))
    restore=ttk.Button(buttons,text='Restaurar versão anterior',command=lambda:run(True));restore.pack(side='left')
    ttk.Label(box,textvariable=status,wraplength=640).pack(anchor='w')
    root.protocol('WM_DELETE_WINDOW',lambda:messagebox.showinfo('Atualizador','Aguarde o término da operação.',parent=root) if busy[0] else root.destroy())
    poll();root.mainloop()

if __name__=='__main__':main()
