"""Build wrapper, retained for existing Windows commands."""
from tools.build_windows import main
if __name__=='__main__':
    try:main()
    except Exception as e:print('ERRO:',e);raise SystemExit(1)
