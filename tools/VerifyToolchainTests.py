#!/usr/bin/env python3
# VerifyToolchainTests.py, Version: 1.00
"""Check rejection gates without downloads or changes to installed tools."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import VerifyToolchain as tool


class Gates(unittest.TestCase):
    def test_missing_environment(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ValueError):
            tool.verify('both')

    def test_sdk_rejections(self):
        lock = json.loads((tool.ROOT / 'Toolchain.lock.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            sdk = Path(directory)
            (sdk / 'tools').mkdir()
            (sdk / 'tools/tools.json').write_text('{}')
            env = {'TAKEOVER_IDF_PATH': directory, 'TAKEOVER_IDF_TOOLS_PATH': directory}
            for head, dirty in [('wrong', ''), (lock['sdk']['commit'], ' M install.sh'), (lock['sdk']['commit'], '')]:
                with patch.dict(os.environ, env), patch.object(tool, 'run', side_effect=[head, dirty]), self.assertRaises(ValueError):
                    tool.verify('both')

    def test_submodule_and_compiler_gates(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'tools').mkdir()
            manifest = {'tools': [{'name': 'compiler', 'versions': [{'name': 'pinned', 'status': 'recommended'}]}]}
            data = json.dumps(manifest).encode()
            (root / 'tools/tools.json').write_bytes(data)
            entry = {'package': 'compiler', 'version': 'pinned', 'directory': 'compiler', 'executable': 'gcc'}
            lock = {'sdk': {'commit': 'expected', 'tools_manifest_sha256': hashlib.sha256(data).hexdigest()}, 'compilers': {'shelly': entry, 'nous': entry}}
            (root / 'Toolchain.lock.json').write_text(json.dumps(lock))
            env = {'TAKEOVER_IDF_PATH': directory, 'TAKEOVER_IDF_TOOLS_PATH': directory}
            for marker in ('-', '+', 'U'):
                with patch.dict(os.environ, env), patch.object(tool, 'ROOT', root), patch.object(tool, 'run', side_effect=['expected', '']), patch.object(tool.subprocess, 'check_output', return_value=marker+'hash path\n'), self.assertRaises(ValueError):
                    tool.verify('both')
            with patch.dict(os.environ, env), patch.object(tool, 'ROOT', root), patch.object(tool, 'run', side_effect=['expected', '', 'wrong compiler']), patch.object(tool.subprocess, 'check_output', return_value=' hash path\n'), self.assertRaises(ValueError):
                tool.verify('shelly')
            with patch.dict(os.environ, env), patch.object(tool, 'ROOT', root), patch.object(tool, 'run', side_effect=['expected', '', 'gcc pinned', 'gcc pinned']), patch.object(tool.subprocess, 'check_output', return_value=' hash path\n'), contextlib.redirect_stdout(io.StringIO()):
                tool.verify('both')


if __name__ == '__main__':
    unittest.main()
