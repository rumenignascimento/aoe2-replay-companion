import ast
from datetime import datetime
from pathlib import Path
import shutil


def main():
    pasta = Path(__file__).resolve().parent
    arquivo = pasta / "painel_movel.py"

    if not arquivo.is_file():
        raise RuntimeError(
            "O módulo móvel ainda não foi instalado nesta pasta.\n"
            "Execute primeiro:\n"
            "py -3.12 instalar_painel_movel.py"
        )

    texto = arquivo.read_text(encoding="utf-8-sig")
    arvore = ast.parse(texto)

    if "menu_celular" in texto:
        print("O menu já está incluído no código.")
        print("Gere e instale a nova versão do aplicativo.")
        return

    codigo_menu = ast.parse("""
menu_atual = self.root.cget("menu")
if menu_atual:
    menu_principal = self.root.nametowidget(menu_atual)
else:
    menu_principal = tk.Menu(self.root)
    self.root.configure(menu=menu_principal)

menu_celular = tk.Menu(menu_principal, tearoff=False)
menu_celular.add_command(
    label="Conectar celular / tablet…",
    command=self.mobile_dialog,
)
menu_principal.add_cascade(
    label="Celular / tablet",
    menu=menu_celular,
)
""").body

    quantidade = 0

    for classe in ast.walk(arvore):
        if (
            isinstance(classe, ast.ClassDef)
            and classe.name == "Window"
        ):
            for metodo in classe.body:
                if (
                    isinstance(metodo, ast.FunctionDef)
                    and metodo.name == "__init__"
                ):
                    metodo.body.extend(codigo_menu)
                    quantidade += 1

    if quantidade != 1:
        raise RuntimeError(
            "Estrutura diferente da esperada. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)
    atualizado = ast.unparse(arvore) + "\n"
    ast.parse(atualizado)

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)
    shutil.copy2(arquivo, backup / arquivo.name)

    arquivo.write_text(atualizado, encoding="utf-8")

    print("Menu superior adicionado.")
    print("Backup:", backup)
    print("Agora gere a versão 0.1.5.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)