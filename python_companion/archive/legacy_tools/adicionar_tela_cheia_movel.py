import ast
from datetime import datetime
from pathlib import Path
import re
import shutil


CSS = r'''
.fullscreen-controls {
    display: flex;
    justify-content: flex-end;
    margin-top: 10px;
}
.fullscreen-controls button {
    width: 100%;
}
body.map-fullscreen-active {
    overflow: hidden;
}
#mapPanel.map-expanded {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    margin: 0;
    border: 0;
    border-radius: 0;
    background: #101719;
    height: 100vh;
    height: 100dvh;
    padding: 12px;
    padding:
        max(12px, env(safe-area-inset-top))
        max(12px, env(safe-area-inset-right))
        max(12px, env(safe-area-inset-bottom))
        max(12px, env(safe-area-inset-left));
}
#mapPanel.map-expanded .tools,
#mapPanel.map-expanded .zoom,
#mapPanel.map-expanded .fullscreen-controls,
#mapPanel.map-expanded #status {
    flex-shrink: 0;
}
#mapPanel.map-expanded #viewport {
    flex: 1;
    min-height: 0;
    max-height: none;
    overscroll-behavior: contain;
}
'''

JAVASCRIPT = r'''
const mapPanel = document.querySelector('main > section');
mapPanel.id = 'mapPanel';

const fullscreenButton =
    document.getElementById('mapFullscreen');

let mapExpanded = false;
let nativeMapFullscreen = false;
let savedScroll = 0;

function fullscreenElement() {
    return document.fullscreenElement ||
           document.webkitFullscreenElement;
}

function setMapExpanded(value) {
    if (value && !mapExpanded) {
        savedScroll = window.scrollY;
    }

    mapExpanded = value;
    mapPanel.classList.toggle('map-expanded', value);
    document.body.classList.toggle(
        'map-fullscreen-active', value
    );

    fullscreenButton.textContent = value
        ? 'Sair da tela cheia'
        : 'Minimapa em tela cheia';

    fullscreenButton.setAttribute(
        'aria-pressed', String(value)
    );

    if (!value) {
        nativeMapFullscreen = false;
        window.scrollTo(0, savedScroll);
    }
}

async function toggleMapFullscreen() {
    if (mapExpanded) {
        if (fullscreenElement() === mapPanel) {
            const exit = document.exitFullscreen ||
                         document.webkitExitFullscreen;

            if (exit) {
                try {
                    await exit.call(document);
                } catch (error) {
                    return;
                }
            }
        }

        setMapExpanded(false);
        return;
    }

    setMapExpanded(true);

    const request = mapPanel.requestFullscreen ||
                    mapPanel.webkitRequestFullscreen;

    if (request) {
        try {
            await request.call(mapPanel);
            nativeMapFullscreen =
                fullscreenElement() === mapPanel;
        } catch (error) {
            nativeMapFullscreen = false;
        }
    }
}

fullscreenButton.addEventListener(
    'click', toggleMapFullscreen
);

function syncMapFullscreen() {
    if (fullscreenElement() === mapPanel) {
        nativeMapFullscreen = true;
    } else if (nativeMapFullscreen) {
        setMapExpanded(false);
    }
}

document.addEventListener(
    'fullscreenchange', syncMapFullscreen
);
document.addEventListener(
    'webkitfullscreenchange', syncMapFullscreen
);

document.addEventListener('keydown', event => {
    if (
        event.key === 'Escape' &&
        mapExpanded &&
        !nativeMapFullscreen
    ) {
        setMapExpanded(false);
    }
});
'''


def main():
    pasta = Path(__file__).resolve().parent
    arquivo = pasta / "painel_movel.py"

    if not arquivo.is_file():
        raise RuntimeError(
            "Coloque este script na pasta que contém "
            "painel_movel.py."
        )

    arvore = ast.parse(
        arquivo.read_text(encoding="utf-8-sig")
    )

    encontrados = [
        item for item in arvore.body
        if isinstance(item, ast.Assign)
        and any(
            isinstance(alvo, ast.Name)
            and alvo.id == "HTML"
            for alvo in item.targets
        )
    ]

    if (
        len(encontrados) != 1
        or not isinstance(
            encontrados[0].value, ast.Constant
        )
        or not isinstance(
            encontrados[0].value.value, str
        )
    ):
        raise RuntimeError(
            "Interface móvel diferente do esperado. "
            "Nenhum arquivo foi alterado."
        )

    html = encontrados[0].value.value

    if 'id="mapFullscreen"' in html:
        print(
            "A opção de tela cheia já está incluída. "
            "Gere e instale a atualização."
        )
        return

    botao = (
        '<div class="fullscreen-controls">'
        '<button id="mapFullscreen" type="button" '
        'aria-pressed="false">'
        'Minimapa em tela cheia'
        '</button></div>\n'
    )

    html, quantidade = re.subn(
        r"""<div\s+class=["']zoom["']\s*>""",
        lambda resultado: botao + resultado.group(),
        html,
        count=1,
    )

    if (
        quantidade != 1
        or "</style>" not in html
        or "</script>" not in html
    ):
        raise RuntimeError(
            "Estrutura da página não reconhecida. "
            "Nenhum arquivo foi alterado."
        )

    html = html.replace(
        "</style>", CSS + "\n</style>", 1
    ).replace(
        "</script>", JAVASCRIPT + "\n</script>", 1
    )

    html = re.sub(
        r'(<span class="badge">)v[0-9.]+',
        r"\g<1>v0.1.7",
        html,
        count=1,
    )

    encontrados[0].value = ast.Constant(html)

    for item in arvore.body:
        if (
            isinstance(item, ast.Assign)
            and any(
                isinstance(alvo, ast.Name)
                and alvo.id == "VERSION"
                for alvo in item.targets
            )
        ):
            item.value = ast.Constant("0.1.7")

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

    print("\nTela cheia adicionada.")
    print("Backup:", backup)
    print("\nExecute:")
    print("py -3.12 gerar_atualizacao.py")
    print("Informe a versão 0.1.7.")


if __name__ == "__main__":
    try:
        main()
    except Exception as erro:
        print("\nERRO:", erro)
        raise SystemExit(1)