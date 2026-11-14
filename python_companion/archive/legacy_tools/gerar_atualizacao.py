import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def main():
    pasta = Path(__file__).resolve().parent
    gerador = pasta / "gerar_instalador.py"
    controle = pasta / "ultima_versao_gerada.json"

    if not gerador.is_file():
        raise RuntimeError(
            "Coloque este arquivo na mesma pasta de gerar_instalador.py."
        )

    anterior = "0.1.0"
    if controle.exists():
        anterior = json.loads(
            controle.read_text(encoding="utf-8")
        )["versao"]

    print(f"Última versão registrada: {anterior}")
    versao = input("Nova versão, por exemplo 0.1.1: ").strip()

    if not re.fullmatch(r"\d+\.\d+\.\d+", versao):
        raise ValueError("Use três números: 0.1.1, 0.2.0 ou 1.0.0.")

    numeros = lambda valor: tuple(map(int, valor.split(".")))

    if numeros(versao) <= numeros(anterior):
        raise ValueError(
            f"A nova versão precisa ser maior que {anterior}."
        )

    codigo = gerador.read_text(encoding="utf-8-sig")

    if "0.1.0" not in codigo:
        raise RuntimeError(
            "O gerador foi modificado e não contém a versão-base 0.1.0. "
            "Envie o arquivo para adaptarmos."
        )

    # Altera somente uma cópia temporária do gerador.
    codigo = codigo.replace("0.1.0", versao)

    temporario = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            prefix="_compilar_atualizacao_",
            dir=pasta,
            encoding="utf-8",
            delete=False,
        ) as arquivo:
            arquivo.write(codigo)
            temporario = Path(arquivo.name)

        subprocess.run(
            [sys.executable, str(temporario)],
            cwd=pasta,
            check=True,
        )

        controle.write_text(
            json.dumps({"versao": versao}, indent=2),
            encoding="utf-8",
        )

        print(f"\nInstalador da versão {versao} gerado.")
        print("Feche o aplicativo antes de instalar a atualização.")

    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print(f"\nERRO: {erro}")
        sys.exit(1)