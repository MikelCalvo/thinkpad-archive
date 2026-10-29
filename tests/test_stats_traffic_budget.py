"""Keep fixed HTML snapshots inside the existing 128 MiB service budget."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]


class DocumentMemoryBudget(unittest.TestCase):
    def test_generated_root_does_not_require_unbounded_resident_html(self):
        program=r'''
from pathlib import Path
import resource
import tempfile
from thinkpad_archive.stats_server import create_server
with tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp);site=base/'site';(site/'en/models').mkdir(parents=True)
    (site/'index.html').write_text('<html lang="en"></html>')
    (site/'en/index.html').write_text('<html lang="en"></html>')
    for i in range(160):
        (site/'en/models'/('m'+str(i)+'.html')).write_text('<html>'+('x'*700000)+'</html>')
    private=base/'private';private.mkdir(mode=0o700)
    resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
    server=create_server(site,private/'counts.sqlite','http://127.0.0.1:8080',enabled=True)
    server.server_close()
'''
        result=subprocess.run([sys.executable,'-B','-c',program],cwd=ROOT,capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
