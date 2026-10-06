#!/usr/bin/env python3
# PreparePrivate.py, Version: 1.02
"""Validate external secrets/keys and generate private headers without logging values."""
import argparse
import json
import os
from pathlib import Path
import subprocess

FIELDS = ('WlanSsid', 'WlanPw', 'WlanSsid2', 'WlanPw2')


def command(args):
    result = subprocess.run(args, input=b'', capture_output=True)
    if result.returncode:
        raise ValueError('Key validation failed (key contents/errors suppressed)')
    return result.stdout


def prepare(private, target, output):
    secrets = json.loads((private / 'Secrets.local.json').read_text())
    if not isinstance(secrets, dict):
        raise ValueError('Secrets root must be an object')
    config = {k: v for k, v in secrets.items() if not isinstance(v, dict)}
    projects = secrets.get('Projects', {})
    if not isinstance(projects, dict):
        raise ValueError('Secrets Projects section must be an object')
    for layer in [secrets.get('Common', {}), secrets.get(target, {}),
                  projects.get(target, {})]:
        if not isinstance(layer, dict):
            raise ValueError('Secrets project/common section must be an object')
        config.update(layer)
    for name in FIELDS:
        value = config.get(name, '')
        if not isinstance(value, str) or '\0' in value:
            raise ValueError('Invalid WLAN field: ' + name)
        size = len(value.encode('utf-8'))
        if 'Ssid' in name and size > 31:
            raise ValueError('SSID exceeds supported runtime length: ' + name)
        if 'Pw' in name and value and not (8 <= size <= 63 or size == 64 and all(c in '0123456789abcdefABCDEF' for c in value)):
            raise ValueError('Invalid WPA password format: ' + name)
        config[name] = value
    if not config['WlanSsid']:
        raise ValueError('Primary WLAN SSID is required')
    private_key = private / 'private.key'
    public_key = private / 'public.key'
    command(['openssl', 'rsa', '-in', str(private_key), '-check', '-noout'])
    actual = command(['openssl', 'pkey', '-in', str(private_key), '-pubout', '-outform', 'DER'])
    expected = command(['openssl', 'pkey', '-pubin', '-in', str(public_key), '-outform', 'DER'])
    if actual != expected:
        raise ValueError('Private/public signing keys do not match')
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    lines = ['#pragma once', '#define ESP_RESCUE_PROJECT_NAME ' + json.dumps(target),
             '#define ESP_RESCUE_VERSION "1.00"']
    for name, macro in zip(FIELDS, ['SSID', 'PW', 'SSID2', 'PW2']):
        lines.append('#define ESP_RESCUE_WLAN_' + macro + ' ' + json.dumps(config[name], ensure_ascii=True))
    path = output / 'EspRescueProject.h'
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', choices=['ShellyTakeover', 'NousTakeover'])
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        prepare(Path(os.environ['TAKEOVER_PRIVATE_DIR']).resolve(), args.target, args.output)
    except (ValueError, KeyError, OSError) as error:
        # JSON decoder errors can include private source text; never reproduce them.
        if isinstance(error, json.JSONDecodeError):
            raise SystemExit('Private configuration is not valid JSON')
        if isinstance(error, OSError):
            raise SystemExit('Private input could not be read/processed')
        raise SystemExit(str(error))
    print('Private WLAN header prepared; RSA key pair verified; values not displayed.')
