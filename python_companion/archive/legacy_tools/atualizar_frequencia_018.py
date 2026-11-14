import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


class FrequenciaPC(ast.NodeTransformer):
    def __init__(self):
        self.encontrou = False

    def visit_Assign(self, node):
        self.generic_visit(node)

        alvo_correto = any(
            isinstance(alvo, ast.Attribute)
            and isinstance(alvo.value, ast.Name)
            and alvo.value.id == "self"
            and alvo.attr == "next_frame"
            for alvo in node.targets
        )

        if (
            alvo_correto
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.op, ast.Add)
            and isinstance(node.value.left, ast.Name)
            and node.value.left.id == "now"
            and isinstance(node.value.right, ast.Constant)
            and node.value.right.value in (1, 5)
        ):
            node.value.right = ast.Constant(1)
            self.encontrou = True

        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            texto = node.value.replace(
                "Atualização-alvo: 5s.",
                "Atualização-alvo: 1s.",
            )
            return ast.copy_location(
                ast.Constant(texto), node
            )
        return node


def main():
    pasta = Path(__file__).resolve().parent
    pc = pasta / "mapa_overlay.py"
    movel = pasta / "painel_movel.py"

    if not pc.is_file() or not movel.is_file():
        raise RuntimeError(
            "Coloque este script na pasta com "
            "mapa_overlay.py e painel_movel.py."
        )

    adaptador = FrequenciaPC()
    arvore_pc = adaptador.visit(ast.parse(
        pc.read_text(encoding="utf-8-sig")
    ))

    if not adaptador.encontrou:
        raise RuntimeError(
            "Agendamento do PC diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    arvore_movel = ast.parse(
        movel.read_text(encoding="utf-8-sig")
    )
    encontrou_html = False

    for item in arvore_movel.body:
        if not isinstance(item, ast.Assign):
            continue

        nomes = [
            alvo.id for alvo in item.targets
            if isinstance(alvo, ast.Name)
        ]

        if (
            "HTML" in nomes
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        ):
            html, quantidade = re.subn(
                r"setInterval\s*\(\s*update\s*,"
                r"\s*(?:5000|1000)\s*\)",
                "setInterval(update, 1000)",
                item.value.value,
            )

            if quantidade != 1:
                raise RuntimeError(
                    "Temporizador móvel diferente do esperado. "
                    "Nenhum arquivo foi alterado."
                )

            html = html.replace(
                "Atualização-alvo: 5 segundos.",
                "Atualização-alvo: 1 segundo.",
            )
            html = re.sub(
                r'(<span class="badge">)v[0-9.]+',
                r"\g<1>v0.1.8",
                html,
                count=1,
            )

            item.value = ast.Constant(html)
            encontrou_html = True

        elif "VERSION" in nomes:
            item.value = ast.Constant("0.1.8")

    if not encontrou_html:
        raise RuntimeError(
            "Interface móvel não reconhecida. "
            "Nenhum arquivo foi alterado."
        )

    alterados = {}

    for nome, arvore in (
        ("mapa_overlay.py", arvore_pc),
        ("painel_movel.py", arvore_movel),
    ):
        ast.fix_missing_locations(arvore)
        texto = ast.unparse(arvore) + "\n"
        ast.parse(texto, filename=nome)
        alterados[nome] = texto

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

    print("\nAtualização-alvo: 1 segundo no PC e no celular.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.1.8.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)