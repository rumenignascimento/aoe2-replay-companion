import ast
from datetime import datetime
import io
from pathlib import Path
import re
import shutil


class Adaptar(ast.NodeTransformer):
    def __init__(self):
        self.copia = False
        self.comando = False
        self.janela = False
        self.setup = False

    def visit_Expr(self, node):
        self.generic_visit(node)
        call = node.value

        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name)
            and call.func.value.id == "shutil"
            and call.func.attr == "copytree"
        ):
            self.copia = True
            extra = ast.parse(
                'shutil.copy2('
                'projeto / "icone.ico", fonte / "icone.ico")'
            ).body[0]
            return [node, extra]

        return node

    def visit_List(self, node):
        self.generic_visit(node)
        valores = [
            item.value for item in node.elts
            if isinstance(item, ast.Constant)
            and isinstance(item.value, str)
        ]

        if "PyInstaller" in valores and "--add-data" in valores:
            self.comando = True
            extra = ast.parse(
                '["--icon", fonte / "icone.ico", '
                '"--add-data", '
                'str(fonte / "icone.ico") + ";."]',
                mode="eval",
            ).body
            node.elts.extend(extra.elts)

        return node

    def visit_Constant(self, node):
        if not isinstance(node.value, str):
            return node

        texto = node.value

        if "import painel_jogadores as painel" in texto:
            padrao = (
                r"(?m)^([ \t]*)root\s*=\s*"
                r"painel\.tk\.Tk\(\)[ \t]*$"
            )

            def substituir(resultado):
                espaco = resultado.group(1)
                linhas = [
                    "import ctypes",
                    "from caminhos_app import BUNDLE_DIR",
                    (
                        "ctypes.windll.shell32."
                        "SetCurrentProcessExplicitAppUserModelID"
                        '("AoE2Overlay.Desktop")'
                    ),
                    "root = painel.tk.Tk()",
                    (
                        "root.iconbitmap("
                        'default=str(BUNDLE_DIR / "icone.ico"))'
                    ),
                ]
                return "\n".join(
                    espaco + linha for linha in linhas
                )

            texto, quantidade = re.subn(
                padrao, substituir, texto, count=1
            )
            self.janela = quantidade == 1

        if "[Setup]" in texto and "[Run]" in texto:
            self.setup = True
            texto = texto.replace(
                "[Setup]",
                "[Setup]\nSetupIconFile=src\\icone.ico",
                1,
            )

        return ast.copy_location(ast.Constant(texto), node)


def main():
    pasta = Path(__file__).resolve().parent
    gerador = pasta / "gerar_instalador.py"
    imagem = pasta / "icone.png"

    if not gerador.is_file() or not imagem.is_file():
        raise RuntimeError(
            "Coloque icone.png e este script na mesma "
            "pasta de gerar_instalador.py."
        )

    original = gerador.read_text(encoding="utf-8-sig")

    if "# ICONE_APLICATIVO_V1" in original:
        atualizado = original
        print("Gerador já adaptado. Atualizando a imagem.")
    else:
        adaptador = Adaptar()
        arvore = adaptador.visit(ast.parse(original))
        ast.fix_missing_locations(arvore)

        if not all((
            adaptador.copia,
            adaptador.comando,
            adaptador.janela,
            adaptador.setup,
        )):
            raise RuntimeError(
                "Gerador diferente do esperado. "
                "Nenhum arquivo foi alterado."
            )

        atualizado = (
            "# ICONE_APLICATIVO_V1\n"
            + ast.unparse(arvore)
            + "\n"
        )
        ast.parse(atualizado)

    try:
        from PIL import Image, ImageOps
    except ImportError:
        raise RuntimeError(
            "Execute primeiro:\n"
            "py -3.12 -m pip install Pillow"
        )

    with Image.open(imagem) as entrada:
        figura = ImageOps.exif_transpose(entrada).convert("RGBA")
        tamanho = max(figura.size)

        quadrado = Image.new(
            "RGBA", (tamanho, tamanho), (0, 0, 0, 0)
        )
        quadrado.alpha_composite(
            figura,
            (
                (tamanho - figura.width) // 2,
                (tamanho - figura.height) // 2,
            ),
        )

        resultado = io.BytesIO()
        quadrado.save(
            resultado,
            format="ICO",
            sizes=[
                (n, n)
                for n in (16, 20, 24, 32, 40, 48, 64, 128, 256)
            ],
        )

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for nome in ("gerar_instalador.py", "icone.ico"):
        origem = pasta / nome
        if origem.exists():
            shutil.copy2(origem, backup / nome)

    (pasta / "icone.ico").write_bytes(resultado.getvalue())
    gerador.write_text(atualizado, encoding="utf-8")

    print("\nÍcone aplicado ao gerador.")
    print("Backup:", backup)
    print("\nAgora execute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.1.3.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)