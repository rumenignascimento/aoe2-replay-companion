from pathlib import Path
import tempfile,unittest,zipfile,json,shutil
from unittest.mock import patch
import patch_core as core
from ativar_patches import adaptar

class Patches(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.base=self.root/'base';self.new=self.root/'new';self.install=self.root/'installed';self.zip=self.root/'patch.aoe2patch'
        for folder in (self.base,self.new):
            (folder/'_internal').mkdir(parents=True)
            (folder/'AoE2Overlay.exe').write_bytes(b'exe old')
            (folder/'_internal/data.bin').write_bytes(b'unchanged')
        (self.base/'_internal/removed.bin').write_bytes(b'removed')
        (self.new/'AoE2Overlay.exe').write_bytes(b'exe new')
        (self.new/'_internal/new.bin').write_bytes(b'new')
        shutil.copytree(self.base,self.install)
        self.manifest=core.create_patch(self.base,self.new,self.zip,'0.4.19','0.4.20')
    def test_only_changed_files_packaged(self):
        with zipfile.ZipFile(self.zip) as z:self.assertEqual(set(z.namelist()),{'manifest.json','payload/AoE2Overlay.exe','payload/_internal/new.bin'})
    def test_apply_and_rollback_preserve_config_and_uninstaller(self):
        (self.install/'unins000.exe').write_bytes(b'uninstaller')
        (self.install/'configuracoes_aoe2.json').write_bytes(b'my config')
        core.apply_patch(self.zip,self.install)
        for n,h in self.manifest['target'].items():self.assertEqual(core.sha(self.install/n),h)
        self.assertFalse((self.install/'_internal/removed.bin').exists())
        core.rollback(self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe old')
        self.assertTrue((self.install/'_internal/removed.bin').exists())
        self.assertFalse((self.install/'_internal/new.bin').exists())
        self.assertEqual((self.install/'configuracoes_aoe2.json').read_bytes(),b'my config')
        self.assertEqual((self.install/'unins000.exe').read_bytes(),b'uninstaller')
    def test_wrong_base_rejected_without_mutation(self):
        (self.install/'_internal/data.bin').write_bytes(b'modified')
        with self.assertRaises(ValueError):core.apply_patch(self.zip,self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe old')
    def rewrite(self,transform):
        with zipfile.ZipFile(self.zip) as z:entries={n:z.read(n) for n in z.namelist()}
        transform(entries)
        with zipfile.ZipFile(self.zip,'w') as z:
            for n,b in entries.items():z.writestr(n,b)
    def test_corrupt_payload_rejected(self):
        self.rewrite(lambda e:e.update({'payload/AoE2Overlay.exe':b'bad'}))
        with self.assertRaises(ValueError):core.apply_patch(self.zip,self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe old')
    def test_extra_traversal_entry_rejected(self):
        self.rewrite(lambda e:e.update({'../outside':b'bad'}))
        with self.assertRaises(ValueError):core.apply_patch(self.zip,self.install)
        self.assertFalse((self.root/'outside').exists())
    def test_unsafe_paths_and_hashes(self):
        for name in ('../x','/x','C:/x','a\\x','a//x','.patch_state.json','a./x'):
            with self.subTest(path=name):
                with self.assertRaises(ValueError):core.safe_name(name)
    def test_failure_mid_apply_restores_originals(self):
        actual=core.os.replace
        def fail_once(src,dst):
            if Path(dst).name=='new.bin':raise OSError('simulated disk error')
            return actual(src,dst)
        with patch.object(core.os,'replace',side_effect=fail_once):
            with self.assertRaises(OSError):core.apply_patch(self.zip,self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe old')
        self.assertTrue((self.install/'_internal/removed.bin').exists())
        self.assertFalse((self.install/'_internal/new.bin').exists())
    def test_pending_transaction_recovery(self):
        core.apply_patch(self.zip,self.install)
        state=json.loads((self.install/'.patch_state.json').read_text())
        journal=json.loads((self.install/'.patch_backups'/state['last_backup']/'journal.json').read_text())
        core.atomic_json(self.install/'.patch_transaction.json',journal)
        core.apply_patch(self.zip,self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe new')
    def test_duplicate_apply_rejected(self):
        core.apply_patch(self.zip,self.install)
        with self.assertRaises(ValueError):core.apply_patch(self.zip,self.install)
    def test_concurrent_update_rejected(self):
        (self.install/'.patch_lock').touch()
        with self.assertRaises(ValueError):core.apply_patch(self.zip,self.install)
    def test_versions_and_identical_builds_rejected(self):
        with self.assertRaises(ValueError):core.create_patch(self.base,self.base,self.zip,'1.0.0','1.1.0')
        with self.assertRaises(ValueError):core.create_patch(self.base,self.new,self.zip,'1.0.0','0.9.0')
    def test_two_patches_and_two_rollbacks(self):
        core.apply_patch(self.zip,self.install)
        third=self.root/'third';shutil.copytree(self.new,third)
        (third/'AoE2Overlay.exe').write_bytes(b'third version')
        next_zip=self.root/'next.aoe2patch'
        core.create_patch(self.new,third,next_zip,'0.4.20','0.4.21')
        core.apply_patch(next_zip,self.install)
        core.rollback(self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe new')
        core.rollback(self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe old')
    def test_corrupt_backup_rejected_before_rollback_mutations(self):
        core.apply_patch(self.zip,self.install)
        state=json.loads((self.install/'.patch_state.json').read_text())
        (self.install/'.patch_backups'/state['last_backup']/'files/AoE2Overlay.exe').write_bytes(b'corrupted')
        with self.assertRaises(ValueError):core.rollback(self.install)
        self.assertEqual((self.install/'AoE2Overlay.exe').read_bytes(),b'exe new')
        self.assertTrue((self.install/'_internal/new.bin').exists())
    def test_source_adapter_is_idempotent(self):
        source="""import sys
from pathlib import Path
def main():
    compilador=None
    if compilador is None:raise RuntimeError('Inno ausente')
    comando=[]
    executar(*comando)
    executar(compilador,'instalador.iss')
"""
        result=adaptar(source)
        self.assertEqual(adaptar(result),result)
        self.assertIn('not somente_executavel_patch',result)
        self.assertIn('ultimo_build_patch.json',result)

if __name__=='__main__':unittest.main(verbosity=2)
