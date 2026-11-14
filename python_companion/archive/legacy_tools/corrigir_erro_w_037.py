import ast
import shutil
from datetime import datetime
from pathlib import Path


def corrigir_base(codigo):
    tree = ast.parse(codigo)
    found = False

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "self"
            and node.func.attr == "prepare_fit_photo"
        ):
            node.args = []
            node.keywords = []
            found = True

    if not found:
        raise RuntimeError(
            "Chamada de calibração não encontrada em mapa_overlay.py."
        )

    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


def corrigir_enquadramento(codigo):
    tree = ast.parse(codigo)
    found = False

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and node.name == "prepare_fit_photo"
        ):
            if [a.arg for a in node.args.args] != [
                "self", "width", "height"
            ]:
                raise RuntimeError(
                    "Método de enquadramento diferente do esperado."
                )

            node.args.defaults = [
                ast.Constant(None),
                ast.Constant(None),
            ]

            if "width is None" not in ast.unparse(node):
                node.body[:0] = ast.parse("""
if width is None or height is None:
    area = self.native.game()
    if not area:
        area = (
            0, 0,
            self.root.winfo_screenwidth(),
            self.root.winfo_screenheight()
        )
    width, height = area[2], area[3]
""").body

            found = True

    if not found:
        raise RuntimeError(
            "Método prepare_fit_photo não encontrado."
        )

    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + "\n"


def main():
    root = Path(__file__).resolve().parent

    operations = {
        "mapa_overlay.py": corrigir_base,
        "enquadramento_035.py": corrigir_enquadramento,
    }

    changes = {}

    for name, function in operations.items():
        path = root / name

        if not path.is_file():
            raise RuntimeError(
                "Arquivo ausente: " + name
                + ". Salve este corretor na pasta GeradorMapaAoE2."
            )

        changes[name] = function(
            path.read_text(encoding="utf-8-sig")
        )

    for name, text in changes.items():
        ast.parse(text, filename=name)

    backup = (
        root / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for name in changes:
        shutil.copy2(root / name, backup / name)

    for name, text in changes.items():
        (root / name).write_text(text, encoding="utf-8")

    print("Correção aplicada. Backup:", backup)
    print("Agora execute: py -3.12 gerar_atualizacao.py")
    print("Versão sugerida: 0.3.7 ou superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("ERRO:", erro)
        raise SystemExit(1)