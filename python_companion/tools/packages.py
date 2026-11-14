"""Release artifacts contain compiled builds only, never the project directory."""
from pathlib import Path
import json,zipfile
from patch_core import inventory,fingerprint
from companion_updates.common import version,installed_version


def create_full(build,output,target_version):
    version(target_version)
    actual=installed_version(build)
    if actual and actual!=target_version:raise ValueError('A versão do build difere da versão solicitada.')
    files=inventory(build)
    manifest={'format':2,'app':'AoE2Overlay','version':target_version,'target':files,'target_fingerprint':fingerprint(files)}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'x',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        for name in files:z.write(Path(build)/name,'payload/'+name)
    return manifest
