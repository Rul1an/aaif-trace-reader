"""The rerun must not accept a locally rewritten input pin manifest."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepairRunner(unittest.TestCase):
    def test_rewritten_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / 'repo'
            subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', str(ROOT), str(tree)], check=True)
            shutil.copytree(ROOT / 'inputs', tree / 'inputs')
            manifest = tree / 'results/b658795/inputs.sha256.json'
            manifest.write_text(manifest.read_text() + '\n')
            result = subprocess.run([sys.executable, 'results/b658795-repaired/reproduce.py', str(Path(tmp) / 'out')],
                                    cwd=tree, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, result.stdout)
            self.assertIn('Commit execution sources', result.stderr)
            self.assertFalse((Path(tmp) / 'out/comparison.json').exists())
