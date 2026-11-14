import ast
from datetime import datetime
from pathlib import Path
import shutil


METODO = r'''
def building_filter_controls(self, parent):
    if getattr(parent, "_building_filters_layout", False):
        return
    parent._building_filters_layout = True

    # Reutiliza as mesmas variáveis e seus observadores.
    for child in parent.winfo_children():
        child.destroy()

    definitions = [
        ("Terreno", "map_terrain"),
        ("Construções", "central_buildings"),
        ("Deslocamentos", "troops_map"),
        ("Pesquisas e eras", "research_icons"),
        ("Gaia", "gaia_show"),
        ("Ocultar militares", "hide_military_buildings"),
        ("Ocultar econômicas", "hide_economic_buildings"),
        ("Ocultar casas", "hide_houses"),
    ]

    controls = []

    for label, key in definitions:
        if not hasattr(self, key):
            continue

        control = ttk.Checkbutton(
            parent,
            text="  " + label,
            variable=getattr(self, key),
            style="Switch.TCheckbutton",
            command=self.refresh_central,
        )
        controls.append((key, control))

    positions = {
        "map_terrain": (0, 0),
        "troops_map": (1, 0),
        "central_buildings": (0, 1),
        "research_icons": (1, 1),
        "gaia_show": (2, 1),
        "hide_military_buildings": (0, 2),
        "hide_economic_buildings": (1, 2),
        "hide_houses": (2, 2),
    }

    previous = [None]

    def layout(event=None):
        width = (
            event.width
            if event is not None
            else parent.winfo_width()
        )

        required = max(
            (
                control.winfo_reqwidth()
                for _, control in controls
            ),
            default=180,
        ) + 12

        columns = (
            3 if width >= required * 3
            else 2 if width >= required * 2
            else 1
        )

        if columns == previous[0]:
            return
        previous[0] = columns

        for index in range(3):
            parent.columnconfigure(
                index,
                weight=1 if index < columns else 0,
                minsize=0,
                uniform=(
                    "building_layers"
                    if index < columns else ""
                ),
            )

        for index, (key, control) in enumerate(controls):
            control.grid_forget()

            row, column = (
                positions[key]
                if columns == 3
                else divmod(index, columns)
            )

            control.grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 8),
                pady=3,
            )

    parent.bind("<Configure>", layout, add="+")
    parent.after_idle(layout)
'''


def main():
    pasta = Path(__file__).resolve().parent
    filtros = pasta / "filtros_construcoes.py"
    central = pasta / "central_replay.py"

    if not filtros.is_file() or not central.is_file():
        raise RuntimeError(
            "Coloque este script na pasta que contém "
            "filtros_construcoes.py e central_replay.py."
        )

    arvore = ast.parse(
        filtros.read_text(encoding="utf-8-sig")
    )
    quantidade = 0

    for classe in ast.walk(arvore):
        if (
            isinstance(classe, ast.ClassDef)
            and classe.name == "Window"
        ):
            metodos = [
                item for item in classe.body
                if isinstance(item, ast.FunctionDef)
                and item.name in (
                    "navigate", "building_filter_controls"
                )
            ]

            if metodos:
                classe.body = [
                    item for item in classe.body
                    if item not in metodos
                ]
                classe.body.append(
                    ast.parse(METODO).body[0]
                )
                quantidade += 1

    if quantidade != 1:
        raise RuntimeError(
            "Estrutura dos filtros diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)

    alterados = {
        "filtros_construcoes.py": (
            ast.unparse(arvore) + "\n"
        )
    }

    arvore = ast.parse(
        central.read_text(encoding="utf-8-sig")
    )
    quantidade = 0

    for classe in ast.walk(arvore):
        if (
            isinstance(classe, ast.ClassDef)
            and classe.name == "Window"
        ):
            for metodo in classe.body:
                if (
                    isinstance(metodo, ast.FunctionDef)
                    and metodo.name == "build_central"
                ):
                    quantidade += 1

                    encontrou_area = any(
                        isinstance(item, ast.Name)
                        and item.id == "rows"
                        and isinstance(item.ctx, ast.Store)
                        for item in ast.walk(metodo)
                    )

                    if not encontrou_area:
                        raise RuntimeError(
                            "Área de camadas não reconhecida."
                        )

                    existe = any(
                        isinstance(item, ast.Call)
                        and ast.unparse(item.func)
                        == "self.building_filter_controls"
                        for item in ast.walk(metodo)
                    )

                    if not existe:
                        metodo.body.append(ast.parse(
                            "self.building_filter_controls(rows)"
                        ).body[0])

    if quantidade != 1:
        raise RuntimeError(
            "Estrutura da central diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    ast.fix_missing_locations(arvore)
    alterados["central_replay.py"] = (
        ast.unparse(arvore) + "\n"
    )

    arquivo_ajuda = pasta / "ajuda_replay.py"

    if arquivo_ajuda.exists():
        arvore = ast.parse(
            arquivo_ajuda.read_text(
                encoding="utf-8-sig"
            )
        )

        for item in arvore.body:
            if (
                isinstance(item, ast.Assign)
                and any(
                    isinstance(alvo, ast.Name)
                    and alvo.id == "TOPICS"
                    for alvo in item.targets
                )
                and isinstance(item.value, ast.List)
            ):
                topicos = ast.literal_eval(item.value)
                atualizados = []

                for titulo, corpo in topicos:
                    if titulo == "Ocultar construções por tipo":
                        corpo = corpo.replace(
                            "Abra Minimapa e localize "
                            "Ocultar ícones de construções.",
                            "Na tela principal, localize os "
                            "controles em Camadas e informações.",
                        )
                    atualizados.append((titulo, corpo))

                item.value = ast.parse(
                    repr(atualizados), mode="eval"
                ).body

        ast.fix_missing_locations(arvore)
        alterados["ajuda_replay.py"] = (
            ast.unparse(arvore) + "\n"
        )

    for nome, codigo in alterados.items():
        ast.parse(codigo, filename=nome)

    backup = (
        pasta / "backups_atualizacoes"
        / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    )
    backup.mkdir(parents=True)

    for nome in alterados:
        shutil.copy2(
            pasta / nome, backup / nome
        )

    for nome, codigo in alterados.items():
        (pasta / nome).write_text(
            codigo, encoding="utf-8"
        )

    print("\nControles movidos para Camadas e informações.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe 0.2.8 ou uma versão superior à última gerada.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)