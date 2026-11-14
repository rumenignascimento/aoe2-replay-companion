import json,os,time,tkinter as tk,unittest,urllib.error
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from companion_updates import controller,trusted_keys
from tools.signing import sign,public_entry
from patch_core import inventory,fingerprint
from companion_updates.config import REPOSITORY

@unittest.skipUnless(os.name=='nt' or os.environ.get('DISPLAY'),'Requires a display for Tk smoke tests')
class ControllerGUI(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.dir=Path(self.temp.name)
        self.root=tk.Tk();self.root.geometry('900x500');self.root.report_callback_exception=lambda *args:self.fail(str(args))
        self.addCleanup(self.destroy)
        app=self.dir/'app';app.mkdir();(app/'AoE2Overlay.exe').write_bytes(b'old')
        (app/'build-info.json').write_text(json.dumps({'version':'0.5.0','managed_files':['AoE2Overlay.exe','build-info.json']}))
        self.app=app;self.window=SimpleNamespace(root=self.root,close=self.root.destroy)
        self.patchers=[]
        for obj,name,value in [(controller,'install_dir',lambda:app),(controller,'data_dir',lambda:self.dir/'data')]:
            p=patch.object(obj,name,value);p.start();self.patchers.append(p)
        self.addCleanup(lambda:[p.stop() for p in self.patchers])
        key=Ed25519PrivateKey.generate();kid,pub=public_entry(key)
        p=patch.object(trusted_keys,'PUBLIC_KEYS',{kid:pub});p.start();self.patchers.append(p)
        package={'kind':'full','filename':'AoE2Overlay-0.5.1-full.aoe2patch','url':f'https://github.com/{REPOSITORY}/releases/download/v0.5.1/AoE2Overlay-0.5.1-full.aoe2patch','version':'0.5.1','size':3,'sha256':'a'*64,'target_fingerprint':'b'*64}
        self.raw=json.dumps(sign({'schema':2,'app':'AoE2Overlay','repository':REPOSITORY,'version':'0.5.1','notes':'Update','packages':[package]},key)).encode()
    def destroy(self):
        try:self.root.destroy()
        except tk.TclError:pass
    def until(self,fn,timeout=4):
        end=time.monotonic()+timeout
        while time.monotonic()<end:
            self.root.update()
            if fn():return
            time.sleep(.01)
        self.fail('Timed out')
    def test_startup_downloads_without_manual_click_and_ui_responds(self):
        ticks=[0]
        def heartbeat():
            ticks[0]+=1;self.root.after(10,heartbeat)
        heartbeat()
        def slow_download(asset,directory,*args):
            time.sleep(.25);path=Path(directory)/asset['filename'];path.write_bytes(b'new');return path
        with patch.object(controller.transport,'fetch_manifest',return_value=self.raw) as fetch,patch.object(controller.transport,'download',side_effect=slow_download) as download:
            manager=controller.UpdateController(self.window)
            self.until(lambda:manager.state=='ready')
            fetch.assert_called_once();download.assert_called_once()
            self.assertGreater(ticks[0],50)
            self.assertTrue(manager.banner.winfo_ismapped())
            manager.open_dialog();self.root.update();self.assertEqual(str(manager.install_button.cget('state')),'normal')
    def test_offline_does_not_interrupt_application(self):
        with patch.object(controller.transport,'fetch_manifest',side_effect=urllib.error.URLError('offline')):
            manager=controller.UpdateController(self.window)
            self.until(lambda:manager.state=='error')
            self.assertTrue(self.root.winfo_exists())
            self.assertIsNone(manager.dialog_window)
            self.assertIsNone(manager.pending)
