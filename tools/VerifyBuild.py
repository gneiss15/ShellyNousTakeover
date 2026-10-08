#!/usr/bin/env python3
# VerifyBuild.py, Version: 1.02
"""Verify ESP image structure, SDK settings, geometry and signed Rescue payloads."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = {key: value for key, value in (line.strip().split('=', 1) for line in (ROOT/'Versions.txt').read_text().splitlines() if line.strip() and not line.lstrip().startswith('#'))}


def verify_image(path, chip, maximum, version=None):
    data = path.read_bytes()
    assert 24 <= len(data) <= maximum, 'Image size outside partition'
    assert data[0] == 0xe9 and struct.unpack_from('<H', data, 12)[0] == chip, 'Wrong chip/image header'
    assert data[2] == 2, 'DIO mode required'
    end = 24
    checksum = 0xef
    for _ in range(data[1]):
        size = struct.unpack_from('<I', data, end + 4)[0]
        end += 8
        assert end + size <= len(data), 'Truncated segment'
        for value in data[end:end + size]:
            checksum ^= value
        end += size
    checksum_pos = (end // 16 + 1) * 16 - 1
    assert data[checksum_pos] == checksum, 'Bad segment checksum'
    if data[23]:
        digest_start = checksum_pos + 1
        assert data[digest_start:digest_start + 32] == hashlib.sha256(data[:digest_start]).digest(), 'Bad ESP appended digest'
    if version:
        assert data[48:80].split(b'\0')[0].decode() == version, 'Wrong Rescue descriptor version'
    return len(data)


def main():
    report_path = ROOT/'BuildResults.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    results = list(report.get('results', []))
    for target, chip, table, flash, rescue_size, loader_size in [
        ('ShellyTakeover', 5, '0x10000', '8MB', 0x180000, 0x6000),
        ('NousTakeover', 0, '0x8000', '4MB', 0xd0000, 0x7000)]:
        for component, name, size in [('Rescue', 'Rescue.bin', rescue_size), ('Bootloader', 'Bootloader.bin', loader_size)]:
            directory = ROOT/'generated'/target/component
            version_key = 'ShellyRescue' if target == 'ShellyTakeover' else 'NousRescue'
            count = verify_image(directory/name, chip, size, VERSIONS[version_key] if component=='Rescue' else None)
            config = (directory/'sdkconfig').read_text()
            assert 'CONFIG_PARTITION_TABLE_OFFSET='+table+'\n' in config
            assert 'CONFIG_ESPTOOLPY_FLASHSIZE_'+flash+'=y\n' in config
            if component=='Rescue':
                assert 'CONFIG_ESP_WIFI_NVS_ENABLED=y' not in config
                assert 'CONFIG_ESP_PHY_CALIBRATION_AND_DATA_STORAGE=y' not in config
                prefix = (directory/'Rescue.signed').read_bytes()
                raw = (directory/name).read_bytes()
                assert prefix.endswith(raw), 'Signed artifact does not contain current payload'
            current = {'target': target, 'component': component,
                       'product_version': VERSIONS[version_key] if component == 'Rescue' else None,
                       'bytes': count, 'chip_checked': True,
                       'image_checksum_checked': True,
                       'sdk_table_offset_checked': True}
            existing_index = next((index for index, item in enumerate(results)
                                   if item.get('target') == target and item.get('component') == component), None)
            if existing_index is None:
                results.append(current)
            else:
                results[existing_index].update(current)
    report.setdefault('version', '1.07')
    report['product_versions'] = VERSIONS
    report.setdefault('hardware_tested', False)
    report['results'] = results
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
