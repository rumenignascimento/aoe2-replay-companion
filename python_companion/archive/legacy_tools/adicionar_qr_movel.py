import ast
from datetime import datetime
from pathlib import Path
import shutil


METODO = r'''
def mobile_dialog(self):
    if self.mobile_popup and self.mobile_popup.winfo_exists():
        self.mobile_popup.lift()
        return

    top = tk.Toplevel(self.root)
    self.mobile_popup = top
    top.title("Conectar celular ou tablet · QR Code")
    top.geometry(
        f"640x{min(680, top.winfo_screenheight() - 100)}"
    )

    page = ttk.Frame(top, padding=16)
    page.pack(fill="both", expand=True)

    ttk.Label(
        page,
        text="Aponte a câmera do celular para o QR Code.",
        font=("Segoe UI", 12, "bold"),
    ).pack(anchor="w")

    ttk.Label(
        page,
        text=(
            "Use a mesma rede do computador. Se o Windows pedir,\n"
            "permita acesso em redes privadas."
        ),
        wraplength=580,
    ).pack(anchor="w", pady=8)

    ttk.Label(
        page, text="Endereço de conexão:"
    ).pack(anchor="w")

    address = tk.StringVar(master=top)
    selector = ttk.Combobox(
        page,
        textvariable=address,
        state="readonly",
    )
    selector.pack(fill="x", pady=6)

    qr_label = tk.Label(
        page, bg="white", borderwidth=12
    )
    qr_label.pack(pady=10)

    info = tk.StringVar(
        master=top,
        value="Painel desligado. Clique em Iniciar.",
    )
    ttk.Label(
        page, textvariable=info, wraplength=580
    ).pack(anchor="w", pady=6)

    def draw(event=None):
        url = address.get()

        if not url:
            qr_label.configure(
                image="", text="QR Code indisponível"
            )
            top.qr_photo = None
            return

        try:
            import qrcode

            qr = qrcode.QRCode(
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=1,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)

            matrix = qr.get_matrix()
            size = len(matrix)

            original = tk.PhotoImage(
                master=top, width=size, height=size
            )
            pixels = " ".join(
                "{"
                + " ".join(
                    "#000000" if cell else "#ffffff"
                    for cell in row
                )
                + "}"
                for row in matrix
            )
            original.put(pixels)

            scale = max(2, min(6, 280 // size))
            top.qr_photo = original.zoom(scale, scale)

            qr_label.configure(
                image=top.qr_photo, text=""
            )
            info.set(
                "Escaneie o QR Code e abra o link.\n"
                "Se não conectar, selecione outro endereço acima."
            )

        except Exception as error:
            qr_label.configure(
                image="",
                text="Não foi possível gerar o QR Code.",
            )
            top.qr_photo = None
            info.set(
                "O endereço continua disponível para copiar.\n"
                "Detalhes: " + str(error)
            )

    def start():
        try:
            service.start()
            urls = service.urls()
            previous = address.get()

            selector.configure(values=urls)
            address.set(
                previous if previous in urls
                else urls[0] if urls else ""
            )

            draw()

            if not urls:
                info.set(
                    "Não identifiquei o IP local. "
                    "Confira a conexão de rede do PC."
                )

            self.next_frame = 0

        except Exception as error:
            info.set(str(error))

    def stop():
        service.stop()
        selector.configure(values=[])
        address.set("")
        draw()
        info.set(
            "Painel desligado. As conexões foram encerradas."
        )

    def copy_address():
        if address.get():
            self.root.clipboard_clear()
            self.root.clipboard_append(address.get())

    selector.bind("<<ComboboxSelected>>", draw)

    buttons = ttk.Frame(page)
    buttons.pack(fill="x", pady=8)

    ttk.Button(
        buttons,
        text="Iniciar / atualizar QR",
        command=start,
    ).pack(side="left")

    ttk.Button(
        buttons,
        text="Copiar endereço",
        command=copy_address,
    ).pack(side="left", padx=8)

    ttk.Button(
        buttons,
        text="Desligar painel",
        command=stop,
    ).pack(side="left")

    ttk.Label(
        page,
        text=(
            "O programa precisa permanecer aberto no PC.\n"
            "Ao reiniciá-lo, escaneie o novo QR Code."
        ),
        wraplength=580,
    ).pack(anchor="w", pady=6)

    if service.server:
        start()
    else:
        draw()
'''


class AdaptarGerador(ast.NodeTransformer):
    def __init__(self):
        self.dependencias = False
        self.compilacao = False

    def visit_Constant(self, node):
        if (
            isinstance(node.value, str)
            and "mgz @" in node.value
            and "pyinstaller==" in node.value
        ):
            self.dependencias = True
            texto = node.value

            if "qrcode==" not in texto:
                texto = texto.rstrip() + "\nqrcode==8.2\n"

            return ast.copy_location(
                ast.Constant(texto), node
            )

        return node

    def visit_List(self, node):
        self.generic_visit(node)
        valores = [
            item.value for item in node.elts
            if isinstance(item, ast.Constant)
            and isinstance(item.value, str)
        ]

        if "PyInstaller" in valores and "--add-data" in valores:
            self.compilacao = True

            if "qrcode" not in valores:
                node.elts.extend([
                    ast.Constant("--collect-all"),
                    ast.Constant("qrcode"),
                ])

        return node


def main():
    pasta = Path(__file__).resolve().parent
    modulo = pasta / "painel_movel.py"
    gerador = pasta / "gerar_instalador.py"

    if not modulo.is_file() or not gerador.is_file():
        raise RuntimeError(
            "Coloque este script na pasta do projeto com "
            "painel_movel.py e gerar_instalador.py."
        )

    arvore = ast.parse(
        modulo.read_text(encoding="utf-8-sig")
    )
    quantidade = 0

    for classe in ast.walk(arvore):
        if (
            isinstance(classe, ast.ClassDef)
            and classe.name == "Window"
        ):
            for indice, item in enumerate(classe.body):
                if (
                    isinstance(item, ast.FunctionDef)
                    and item.name == "mobile_dialog"
                ):
                    classe.body[indice] = (
                        ast.parse(METODO).body[0]
                    )
                    quantidade += 1

    if quantidade != 1:
        raise RuntimeError(
            "Estrutura do módulo móvel não reconhecida. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)

    adaptador = AdaptarGerador()
    compilacao = adaptador.visit(ast.parse(
        gerador.read_text(encoding="utf-8-sig")
    ))

    if not (
        adaptador.dependencias
        and adaptador.compilacao
    ):
        raise RuntimeError(
            "Gerador diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(compilacao)

    alterados = {
        "painel_movel.py": ast.unparse(arvore) + "\n",
        "gerar_instalador.py": (
            ast.unparse(compilacao) + "\n"
        ),
    }

    for nome, texto in alterados.items():
        ast.parse(texto, filename=nome)

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for nome in alterados:
        shutil.copy2(pasta / nome, backup / nome)

    for nome, texto in alterados.items():
        (pasta / nome).write_text(
            texto, encoding="utf-8"
        )

    print("\nQR Code adicionado.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.1.6.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)