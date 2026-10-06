#!/usr/bin/env python3
# VerifyToolchain.py, Version: 1.00
"""Validate the selected SDK and compiler identities before executing SDK code."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent


def run(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.PIPE).strip()


def verify(target, sdk_only=False):
    lock = json.loads((ROOT / 'Toolchain.lock.json').read_text())
    for name in ('TAKEOVER_IDF_PATH', 'TAKEOVER_IDF_TOOLS_PATH'):
        if not os.environ.get(name):
            raise ValueError('Set ' + name)
    sdk = Path(os.environ['TAKEOVER_IDF_PATH']).resolve()
    tools = Path(os.environ['TAKEOVER_IDF_TOOLS_PATH']).resolve()
    if run(['git', '-C', str(sdk), 'rev-parse', 'HEAD']) != lock['sdk']['commit']:
        raise ValueError('SDK commit differs from Toolchain.lock.json; existing SDK is not changed.')
    if run(['git', '-C', str(sdk), 'status', '--porcelain', '--untracked-files=no']):
        raise ValueError('SDK has tracked changes; existing SDK is not changed.')
    manifest = sdk / 'tools/tools.json'
    if hashlib.sha256(manifest.read_bytes()).hexdigest() != lock['sdk']['tools_manifest_sha256']:
        raise ValueError('SDK tools manifest differs from lock.')
    # Preserve leading status markers; strip() would conceal missing submodules.
    status = subprocess.check_output(['git', '-C', str(sdk), 'submodule', 'status', '--recursive'], text=True)
    if not status or any(line[0] != ' ' for line in status.splitlines()):
        raise ValueError('SDK submodules are missing or differ from their pinned commits.')
    if sdk_only:
        return
    manifest_tools = {item['name']: item for item in json.loads(manifest.read_text())['tools']}
    for name in ('shelly', 'nous') if target == 'both' else (target,):
        entry = lock['compilers'][name]
        recommended = [v['name'] for v in manifest_tools[entry['package']]['versions'] if v['status'] == 'recommended']
        if recommended != [entry['version']]:
            raise ValueError('Compiler recommendation differs from lock: ' + name)
        executable = tools / 'tools' / entry['package'] / entry['version'] / entry['directory'] / 'bin' / entry['executable']
        version = run([str(executable), '--version']).splitlines()[0]
        if entry['version'] not in version:
            raise ValueError('Compiler identity differs from lock: ' + name)
        print(name + ': ' + version)
    print('Pinned SDK and selected compilers verified; no device request.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', choices=('shelly', 'nous', 'both'), default='both')
    parser.add_argument('--sdk-only', action='store_true')
    args = parser.parse_args()
    try:
        verify(args.target, args.sdk_only)
    except (ValueError, OSError, subprocess.CalledProcessError, KeyError) as error:
        # Do not print subprocess output or environment contents.
        message = str(error) if isinstance(error, ValueError) else 'SDK/toolchain unavailable or invalid.'
        print('Toolchain check failed: ' + message, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
