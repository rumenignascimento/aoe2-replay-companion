import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


class PC(ast.NodeTransformer):
    def __init__(self):
        self.encontrou = False

    def visit_Assign(self, node):
        self.generic_visit(node)

        alvo = any(
            isinstance(item, ast.Attribute)
            and isinstance(item.value, ast.Name)
            and item.value.id == "self"
            and item.attr == "next_frame"
            for item in node.targets
        )

        if alvo:
            value = node.value

            if isinstance(value, ast.Name) and value.id == "now":
                self.encontrou = True

            elif (
                isinstance(value, ast.BinOp)
                and isinstance(value.op, ast.Add)
                and isinstance(value.left, ast.Name)
                and value.left.id == "now"
                and isinstance(value.right, ast.Constant)
                and value.right.value in (1, 5)
            ):
                node.value = ast.Name(
                    id="now", ctx=ast.Load()
                )
                self.encontrou = True

        return node

    def visit_Call(self, node):
        self.generic_visit(node)

        if (
            isinstance(node.func, ast.Attribute)
            and ast.unparse(node.func) == "self.root.after"
            and len(node.args) == 2
            and ast.unparse(node.args[1]) == "self.tick"
        ):
            node.args[0] = ast.parse(
                "10 if self.busy else "
                "(0 if self.path and now >= self.next_frame else 100)",
                mode="eval",
            ).body

        return node

    def visit_Constant(self, node):
        if isinstance(node.value, str):
            texto = node.value.replace(
                "Atualização-alvo: 1s.",
                "Atualização contínua.",
            ).replace(
                "Atualização-alvo: 5s.",
                "Atualização contínua.",
            )
            return ast.copy_location(
                ast.Constant(texto), node
            )
        return node


class Mobile(ast.NodeTransformer):
    def __init__(self):
        self.lock = False
        self.wait = False
        self.publish = False

    def visit_Assign(self, node):
        self.generic_visit(node)

        if any(
            ast.unparse(alvo) == "self.lock"
            for alvo in node.targets
        ):
            node.value = ast.parse(
                "threading.Condition(threading.RLock())",
                mode="eval",
            ).body
            self.lock = True

        return node

    def visit_With(self, node):
        self.generic_visit(node)

        contextos = [
            ast.unparse(item.context_expr)
            for item in node.items
        ]
        service_lock = "service.lock" in contextos
        self_lock = "self.lock" in contextos

        if not (service_lock or self_lock):
            return node

        codigo = ast.unparse(node)

        leitura = service_lock and any(
            isinstance(item, ast.Assign)
            and any(
                isinstance(alvo, ast.Name)
                and alvo.id == "snap"
                for alvo in item.targets
            )
            for item in node.body
        )

        if leitura:
            self.wait = True

            if "_continuous_requested" not in codigo:
                espera = """
if resource == "state":
    from urllib.parse import parse_qs
    _continuous_requested = parse_qs(
        urlsplit(self.path).query
    ).get("r", [""])[0]

    if (
        service.snapshot is None
        or service.snapshot["state"]["revision"]
        == _continuous_requested
    ):
        service.lock.wait_for(
            lambda: (
                service.server is None
                or (
                    service.snapshot is not None
                    and service.snapshot["state"]["revision"]
                    != _continuous_requested
                )
            ),
            timeout=20,
        )
"""
                node.body = ast.parse(espera).body + node.body

        dono = "service" if service_lock else "self"

        publica = any(
            isinstance(item, ast.Assign)
            and any(
                ast.unparse(alvo) == dono + ".snapshot"
                for alvo in item.targets
            )
            for item in node.body
        )

        if publica:
            if service_lock and "service.serial" in codigo:
                self.publish = True

            ja_notifica = any(
                isinstance(item, ast.Expr)
                and isinstance(item.value, ast.Call)
                and ast.unparse(item.value.func)
                == dono + ".lock.notify_all"
                for item in node.body
            )

            if not ja_notifica:
                node.body.append(ast.parse(
                    dono + ".lock.notify_all()"
                ).body[0])

        return node


def alterar_html(html):
    if "let continuousRetry" not in html:
        html, quantidade = re.subn(
            r"setInterval\s*\(\s*update\s*,"
            r"\s*(?:1000|5000)\s*\)\s*;?",
            "",
            html,
        )
        if quantidade != 1:
            raise RuntimeError(
                "Temporizador da página diferente do esperado."
            )

        agendamento = """
let continuousRetry = 0;
let continuousTimer;

function scheduleContinuousUpdate() {
    clearTimeout(continuousTimer);

    if (!document.hidden) {
        continuousTimer = setTimeout(
            update,
            continuousRetry
                ? Math.min(10000, 500 * 2 ** continuousRetry)
                : 0
        );
    }
}
"""

        html, quantidade = re.subn(
            r"async\s+function\s+update\s*\(\s*\)\s*\{",
            lambda resultado: (
                agendamento + resultado.group()
                + "\nclearTimeout(continuousTimer);"
            ),
            html,
            count=1,
        )
        if quantidade != 1:
            raise RuntimeError(
                "Função de atualização móvel não reconhecida."
            )

        html, quantidade = re.subn(
            r"((?:const|let)\s+\w+\s*=\s*await\s+"
            r"response\.json\(\)\s*;?)",
            lambda resultado: (
                resultado.group() + "\ncontinuousRetry = 0;"
            ),
            html,
            count=1,
        )
        if quantidade != 1:
            raise RuntimeError(
                "Resposta móvel não reconhecida."
            )

        html, quantidade = re.subn(
            r"""(catch\s*\([^)]*\)\s*\{\s*)"""
            r"""(status\.textContent\s*=\s*['"]Sem conex)""",
            lambda resultado: (
                resultado.group(1)
                + "continuousRetry = "
                "Math.min(6, continuousRetry + 1);\n"
                + resultado.group(2)
            ),
            html,
            count=1,
        )
        if quantidade != 1:
            raise RuntimeError(
                "Tratamento de conexão móvel não reconhecido."
            )

        html, quantidade = re.subn(
            r"(finally\s*\{\s*clearTimeout\(timeout\);"
            r"\s*busy\s*=\s*false\s*;?)",
            lambda resultado: (
                resultado.group()
                + "\nscheduleContinuousUpdate();"
            ),
            html,
            count=1,
        )
        if quantidade != 1:
            raise RuntimeError(
                "Finalização da consulta móvel não reconhecida."
            )

        html = re.sub(
            r"(if\s*\(\s*response\.status\s*===\s*401"
            r"\s*\)\s*\{)",
            r"\g<1>continuousRetry = 6;",
            html,
            count=1,
        )

        html = html.replace(
            "controller.abort(),8000",
            "controller.abort(),25000",
        )
        html = re.sub(
            r"(controller\.abort\(\)\s*,\s*)8000",
            r"\g<1>25000",
            html,
        )

    html = html.replace(
        "Atualização-alvo: 1 segundo.",
        "Atualização contínua.",
    ).replace(
        "Atualização-alvo: 5 segundos.",
        "Atualização contínua.",
    ).replace(
        "Conectando ao computador…",
        "Aguardando dados do computador…",
    )

    return re.sub(
        r'(<span class="badge">)v[0-9.]+',
        r"\g<1>v0.2.2",
        html,
        count=1,
    )


def main():
    pasta = Path(__file__).resolve().parent

    for nome in ("mapa_overlay.py", "painel_movel.py"):
        if not (pasta / nome).is_file():
            raise RuntimeError("Arquivo ausente: " + nome)

    adaptador_pc = PC()
    pc = adaptador_pc.visit(ast.parse(
        (pasta / "mapa_overlay.py").read_text(
            encoding="utf-8-sig"
        )
    ))
    if not adaptador_pc.encontrou:
        raise RuntimeError(
            "Agendamento do PC não reconhecido."
        )

    adaptador_movel = Mobile()
    movel = adaptador_movel.visit(ast.parse(
        (pasta / "painel_movel.py").read_text(
            encoding="utf-8-sig"
        )
    ))

    if not all((
        adaptador_movel.lock,
        adaptador_movel.wait,
        adaptador_movel.publish,
    )):
        raise RuntimeError(
            "Servidor móvel diferente do esperado."
        )

    encontrou = False

    for item in movel.body:
        if not isinstance(item, ast.Assign):
            continue

        nomes = [
            alvo.id for alvo in item.targets
            if isinstance(alvo, ast.Name)
        ]

        if "HTML" in nomes:
            item.value = ast.Constant(
                alterar_html(item.value.value)
            )
            encontrou = True

        elif "VERSION" in nomes:
            item.value = ast.Constant("0.2.2")

    if not encontrou:
        raise RuntimeError("Página móvel não encontrada.")

    alterados = {}

    for nome, arvore in (
        ("mapa_overlay.py", pc),
        ("painel_movel.py", movel),
    ):
        ast.fix_missing_locations(arvore)
        texto = ast.unparse(arvore) + "\n"
        ast.parse(texto)
        alterados[nome] = texto

    central = pasta / "central_replay.py"

    if central.is_file():
        texto = central.read_text(
            encoding="utf-8-sig"
        ).replace(
            "A atualização tem alvo de 1 segundo e aguarda",
            "A atualização é contínua e aguarda",
        )
        ast.parse(texto)
        alterados[central.name] = texto

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

    print("\nAtualização contínua preparada.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.2 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)