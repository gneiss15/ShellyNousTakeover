#!/usr/bin/env python3
# VerifyBuildFiles.py, Version: 1.00
"""Check generated-input stability and failure preservation without device access."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from BuildFiles import copy_file_if_changed, generate_output_if_changed, write_bytes_if_changed


class BuildFileTests(unittest.TestCase):
    def test_unchanged_content_preserves_timestamp_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'private.h'
            self.assertTrue(write_bytes_if_changed(path, b'first'))
            path.chmod(0o600)
            before = path.stat()
            self.assertFalse(write_bytes_if_changed(path, b'first'))
            self.assertEqual(path.stat().st_mtime_ns, before.st_mtime_ns)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(write_bytes_if_changed(path, b'changed'))
            self.assertEqual(path.read_bytes(), b'changed')

    def test_copy_retains_source_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = (Path(directory) / name for name in ('source', 'target'))
            source.write_bytes(b'input')
            source.chmod(0o640)
            self.assertTrue(copy_file_if_changed(source, target))
            self.assertEqual(target.stat().st_mode & 0o777, 0o640)
            before = target.stat().st_mtime_ns
            self.assertFalse(copy_file_if_changed(source, target))
            self.assertEqual(target.stat().st_mtime_ns, before)

    def test_generator_publishes_padded_content_only_when_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'table.bin'
            command = [sys.executable, '-c',
                       'import pathlib,sys;pathlib.Path(sys.argv[1]).write_bytes(b"table")',
                       str(target)]
            self.assertTrue(generate_output_if_changed(command, padding=16))
            self.assertEqual(target.read_bytes(), b'table' + b'\xff' * 11)
            before = target.stat().st_mtime_ns
            self.assertFalse(generate_output_if_changed(command, padding=16))
            self.assertEqual(target.stat().st_mtime_ns, before)
            self.assertEqual(list(Path(directory).glob('.generator-*')), [])

    def test_failed_generator_preserves_previous_output(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'table.bin'
            target.write_bytes(b'valid previous output')
            command = [sys.executable, '-c',
                       'import pathlib,sys;pathlib.Path(sys.argv[1]).write_bytes(b"partial");sys.exit(1)',
                       str(target)]
            with self.assertRaises(subprocess.CalledProcessError):
                generate_output_if_changed(command)
            self.assertEqual(target.read_bytes(), b'valid previous output')
            self.assertEqual(list(Path(directory).glob('.generator-*')), [])


if __name__ == '__main__':
    unittest.main()
