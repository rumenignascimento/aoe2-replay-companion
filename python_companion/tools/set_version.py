from pathlib import Path
import argparse,json
from companion_updates.common import version,write_json

def main():
    p=argparse.ArgumentParser(description='Define a próxima versão antes da compilação.')
    p.add_argument('version');args=p.parse_args();path=Path(__file__).resolve().parents[1]/'version.json'
    current=json.loads(path.read_text(encoding='utf-8'))
    if version(args.version)<=version(current['version']):raise ValueError('A versão deve ser superior à atual.')
    current['version']=args.version;write_json(path,current);print('Versão do projeto:',args.version)
if __name__=='__main__':main()
