from pathlib import Path
import ast,base64,copy,hashlib,importlib.util,io,json,os,shutil,sys,tempfile,unittest,zipfile
from unittest.mock import patch,Mock
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from companion_updates import security,trusted_keys,transport,controller,runner,processes
from companion_updates.common import installed_version,write_json
from companion_updates.config import REPOSITORY
from tools.signing import sign,public_entry,initialize
from tools.packages import create_full
from tools.publish_release import prepare
import patch_core as core


def build(root,ver,content=b'EXE',key_ids=None):
    root=Path(root);(root/'_internal').mkdir(parents=True,exist_ok=True)
    (root/'AoE2Overlay.exe').write_bytes(content)
    (root/'AoE2Updater.exe').write_bytes(b'updater')
    (root/'_internal/data.bin').write_bytes(b'library')
    write_json(root/'build-info.json',{'version':ver,'update_key_ids':key_ids or [],'managed_files':['AoE2Overlay.exe','AoE2Updater.exe','_internal/data.bin','build-info.json']})
    return root


def asset(payload_dir,kind='full',target='b'*64,base='a'*64):
    name='AoE2Overlay-0.5.1-full.aoe2patch'
    data=b'example';path=Path(payload_dir)/name;path.write_bytes(data)
    return {'kind':kind,'filename':name,'url':f'https://github.com/{REPOSITORY}/releases/download/v0.5.1/{name}',
            'version':'0.5.1','size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'target_fingerprint':target,
            **({'base_version':'0.5.0','base_fingerprint':base} if kind=='patch' else {})}


class Updates(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.key=Ed25519PrivateKey.generate();ident,pub=public_entry(self.key);self.ident=ident
        self.keys={ident:pub};self.key_patch=patch.object(trusted_keys,'PUBLIC_KEYS',self.keys);self.key_patch.start();self.addCleanup(self.key_patch.stop)
        self.payload={'schema':2,'app':'AoE2Overlay','repository':REPOSITORY,'version':'0.5.1','notes':'Nova versão','packages':[asset(self.root)]}
    def raw(self,payload=None):return json.dumps(sign(payload or self.payload,self.key)).encode()
    def test_signature_accepts_pinned_publisher(self):self.assertEqual(security.verify(self.raw())['version'],'0.5.1')
    def test_tampering_rejected(self):
        value=json.loads(self.raw());value['payload']['notes']='altered'
        with self.assertRaises(ValueError):security.verify(json.dumps(value).encode())
    def test_unknown_publisher_rejected(self):
        with self.assertRaises(ValueError):security.verify(self.raw(),{})
    def test_unsigned_manifest_rejected(self):
        with self.assertRaises(ValueError):security.verify(json.dumps(self.payload).encode())
    def test_wrong_host_rejected_even_when_signed(self):
        data=copy.deepcopy(self.payload);data['packages'][0]['url']='https://example.org/file'
        with self.assertRaises(ValueError):security.verify(self.raw(data))
    def test_invalid_version_rejected(self):
        data=copy.deepcopy(self.payload);data['version']='../bad'
        with self.assertRaises(ValueError):security.verify(self.raw(data))
    def test_bad_size_and_duplicate_assets_rejected(self):
        for size in (0,-1,True,3*1024**3):
            data=copy.deepcopy(self.payload);data['packages'][0]['size']=size
            with self.assertRaises(ValueError):security.verify(self.raw(data))
        data=copy.deepcopy(self.payload);data['packages']*=2
        with self.assertRaises(ValueError):security.verify(self.raw(data))
    def test_transport_hosts_enforced(self):
        for url in ('http://github.com/x','https://evil.example/x','https://user:password@github.com/x','https://github.com:123/x'):
            with self.assertRaises(ValueError):transport.safe_url(url)
    def test_download_hash_and_partial_cleanup(self):
        a=self.payload['packages'][0]
        class Response(io.BytesIO):
            def geturl(self):return 'https://release-assets.githubusercontent.com/file'
        with patch.object(transport,'open_url',return_value=Response(b'example')):
            path=transport.download(a,self.root/'downloads');self.assertEqual(path.read_bytes(),b'example')
        a=dict(a,sha256='0'*64)
        with patch.object(transport,'open_url',return_value=Response(b'bad')):
            with self.assertRaises(ValueError):transport.download(a,self.root/'downloads')
        self.assertFalse(list((self.root/'downloads').glob('*.download')))
    def test_cached_download_needs_matching_hash(self):
        a=self.payload['packages'][0]
        with patch.object(transport,'open_url',side_effect=AssertionError('network not needed')):
            self.assertEqual(transport.download(a,self.root).read_bytes(),b'example')
    def test_select_patch_then_full_and_never_downgrade(self):
        installed=build(self.root/'app','0.5.0');fp=core.fingerprint(core.inventory(installed))
        data=copy.deepcopy(self.payload);full=data['packages'][0]
        patch_asset=dict(full,kind='patch',filename='update.aoe2patch',base_fingerprint=fp,base_version='0.5.0',size=1)
        data['packages'].append(patch_asset)
        self.assertEqual(controller.choose_package(data,installed)['kind'],'patch')
        data['packages'][1]['base_fingerprint']='c'*64
        self.assertEqual(controller.choose_package(data,installed)['kind'],'full')
        data['version']='0.5.0';self.assertIsNone(controller.choose_package(data,installed))
    def test_full_update_preserves_preferences_uninstaller_and_rollback(self):
        old=build(self.root/'old','0.5.0',b'old');new=build(self.root/'new','0.5.1',b'new')
        (old/'personal-config.json').write_bytes(b'mine');(old/'unins000.exe').write_bytes(b'uninstall')
        archive=self.root/'full.aoe2patch';create_full(new,archive,'0.5.1')
        core.apply_patch(archive,old)
        self.assertEqual(installed_version(old),'0.5.1');self.assertEqual((old/'personal-config.json').read_bytes(),b'mine')
        core.rollback(old);self.assertEqual(installed_version(old),'0.5.0');self.assertEqual((old/'AoE2Overlay.exe').read_bytes(),b'old')
    def test_legacy_migration_by_full_package_keeps_unknown_files(self):
        old=self.root/'legacy';old.mkdir();(old/'AoE2Overlay.exe').write_bytes(b'legacy');(old/'unknown.dat').write_bytes(b'keep')
        new=build(self.root/'new','0.5.1')
        archive=self.root/'full.aoe2patch';create_full(new,archive,'0.5.1');core.apply_patch(archive,old)
        self.assertEqual((old/'unknown.dat').read_bytes(),b'keep')
        self.assertEqual(core.fingerprint(core.inventory(old)),core.fingerprint(core.inventory(new)))
    def test_corrupt_full_payload_no_mutations(self):
        old=build(self.root/'old','0.5.0',b'old');new=build(self.root/'new','0.5.1',b'new')
        archive=self.root/'full.aoe2patch';create_full(new,archive,'0.5.1')
        with zipfile.ZipFile(archive) as z:items={n:z.read(n) for n in z.namelist()}
        items['payload/AoE2Overlay.exe']=b'corrupted'
        with zipfile.ZipFile(archive,'w') as z:
            for n,b in items.items():z.writestr(n,b)
        with self.assertRaises(ValueError):core.apply_patch(archive,old)
        self.assertEqual((old/'AoE2Overlay.exe').read_bytes(),b'old')
    def test_windows_paths_rejected(self):
        for name in ('../a','C:/a','a\\b','CON.txt','a/NUL','a./b','.patch_state.json'):
            with self.assertRaises(ValueError):core.safe_name(name)
    def test_path_tree_collision_rejected(self):
        with self.assertRaises(ValueError):core.check_map({'AoE2Overlay.exe':'a'*64,'a':'b'*64,'a/b':'c'*64})
    def test_delta_format_remains_legacy_compatible(self):
        old=build(self.root/'old','0.5.0',b'old');new=build(self.root/'new','0.5.1',b'new')
        archive=self.root/'delta.aoe2patch';m=core.create_patch(old,new,archive,'0.5.0','0.5.1')
        self.assertEqual(m['format'],1);core.apply_patch(archive,old);core.rollback(old)
        self.assertEqual((old/'AoE2Overlay.exe').read_bytes(),b'old')
    def test_publisher_stages_only_compiled_assets(self):
        new=build(self.root/'new','0.5.1',key_ids=[self.ident])
        folder,v=prepare(new,self.root/'releases',notes='Notes',key=self.key)
        payload=security.verify((folder/'updates.json').read_bytes())
        self.assertEqual(payload['version'],'0.5.1');self.assertFalse(list(folder.rglob('*.py')))
        self.assertFalse(list(folder.rglob('*.pem')))
    def test_publisher_rejects_build_that_does_not_trust_its_key(self):
        new=build(self.root/'new','0.5.1',key_ids=['unrelated'])
        with self.assertRaises(ValueError):prepare(new,self.root/'releases',key=self.key)
        self.assertFalse((self.root/'releases/v0.5.1').exists())
    def test_key_initialization_keeps_secret_outside_public_code(self):
        private=self.root/'publisher/private.pem';public=self.root/'source/trusted_keys.py'
        ident=initialize(private,public);self.assertIn(ident,public.read_text());self.assertNotIn('PRIVATE KEY',public.read_text())
        before=private.read_bytes();initialize(private,public);self.assertEqual(private.read_bytes(),before)
    def test_health_timeout_rolls_back_and_reopens_old_version(self):
        old=build(self.root/'old','0.5.0',b'old');new=build(self.root/'new','0.5.1',b'new',key_ids=[self.ident])
        folder,v=prepare(new,self.root/'releases',key=self.key)
        child=Mock();child.poll.return_value=None
        with patch.object(runner,'spawn',return_value=child),patch.object(runner,'marker',return_value=self.root/'health.json'):
            with self.assertRaisesRegex(RuntimeError,'restaurada'):
                runner.apply_signed(folder/'updates.json',next(folder.glob('*.aoe2patch')),old,health_timeout=0)
        child.terminate.assert_called_once();self.assertEqual((old/'AoE2Overlay.exe').read_bytes(),b'old')
    def test_successful_health_ack_commits_new_version(self):
        old=build(self.root/'old','0.5.0',b'old');new=build(self.root/'new','0.5.1',b'new',key_ids=[self.ident])
        folder,v=prepare(new,self.root/'releases',key=self.key);health=self.root/'health.json'
        def spawn(*a,**kw):
            write_json(health,{'token':kw['extra_env']['AOE2_COMPANION_UPDATE_TOKEN'],'version':'0.5.1','started':True})
            return Mock()
        with patch.object(runner,'spawn',side_effect=spawn),patch.object(runner,'marker',return_value=health):
            runner.apply_signed(folder/'updates.json',next(folder.glob('*.aoe2patch')),old)
        self.assertEqual((old/'AoE2Overlay.exe').read_bytes(),b'new');self.assertFalse(health.exists())
    def test_frozen_spawn_resets_parent_bundle_environment(self):
        bundle=self.root/'bundle';bundle.mkdir()
        with patch.object(processes.sys,'_MEIPASS',str(bundle),create=True),patch.dict(os.environ,{'PATH':str(bundle)+os.pathsep+'/usr/bin','AOE2_COMPANION_UPDATE_TOKEN':'old'}),patch.object(processes.subprocess,'Popen',return_value=Mock()) as popen:
            processes.spawn(['example'])
        env=popen.call_args.kwargs['env']
        self.assertEqual(env['PYINSTALLER_RESET_ENVIRONMENT'],'1')
        self.assertNotIn('AOE2_COMPANION_UPDATE_TOKEN',env)
        self.assertNotIn(str(bundle),env['PATH'].split(os.pathsep))
    def test_generated_launcher_compiles(self):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'tools/build_windows.py').read_text(encoding='utf-8'))
        launchers=[n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'root.report_callback_exception = erro_interface' in n.value]
        import textwrap
        self.assertEqual(len(launchers),1)
        compile(textwrap.dedent(launchers[0]).lstrip(),'iniciar.py','exec')
    def test_bundled_asset_updates_without_touching_preferences(self):
        root=Path(__file__).resolve().parents[1]
        tree=ast.parse((root/'tools/build_windows.py').read_text(encoding='utf-8'))
        source=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Constant) and isinstance(n.value,str) and 'def preparar():' in n.value and 'BUNDLE_DIR' in n.value)
        import textwrap
        namespace={'__file__':str(self.root/'caminhos_app.py')}
        with patch.dict(os.environ,{'LOCALAPPDATA':str(self.root/'localdata')}):
            exec(compile(textwrap.dedent(source).lstrip(),'caminhos_app.py','exec'),namespace)
            icons=self.root/'icones_aoe2';icons.mkdir();(icons/'building.png').write_bytes(b'new asset')
            data=namespace['DATA_DIR'];(data/'icones_aoe2').mkdir(parents=True)
            (data/'icones_aoe2/building.png').write_bytes(b'old asset')
            (data/'configuracoes_aoe2.json').write_bytes(b'personal settings')
            namespace['preparar']()
            self.assertEqual((data/'icones_aoe2/building.png').read_bytes(),b'new asset')
            self.assertEqual((data/'configuracoes_aoe2.json').read_bytes(),b'personal settings')
    def test_runtime_original_sources_preserved(self):
        root=Path(__file__).resolve().parents[1]
        # Source snapshot hashes ensure update refactoring cannot silently alter game behavior.
        snapshot=json.loads((root/'docs/runtime_snapshot.json').read_text())
        for name,expected in snapshot.items():self.assertEqual(hashlib.sha256((root/name).read_text(encoding='utf-8-sig').replace('\r\n','\n').encode('utf-8')).hexdigest(),expected,name)

if __name__=='__main__':unittest.main(verbosity=2)
