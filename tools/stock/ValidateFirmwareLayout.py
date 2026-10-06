#!/usr/bin/env python3
# ValidateFirmwareLayout.py, Version: 1.01
import hashlib
import json
import pathlib
import struct
import sys
import zipfile


def fail(message: str) -> None:
  raise SystemExit(f"Error: {message}")


def sha256(data: bytes) -> str:
  return hashlib.sha256(data).hexdigest()


def parse_partition_table(data: bytes):
  rows = []
  for offset in range(0, min(len(data), 0xC00), 32):
    row = data[offset:offset + 32]
    if len(row) < 32:
      break
    magic, ptype, subtype, address, size, label_raw, flags = struct.unpack("<HBBII16sI", row)
    if magic == 0xFFFF:
      break
    if magic != 0x50AA:
      # MD5 marker or unused padding ends the normal entry list.
      break
    label = label_raw.split(b"\0", 1)[0].decode("ascii", errors="strict")
    rows.append({
      "label": label,
      "type": ptype,
      "subtype": subtype,
      "offset": address,
      "size": size,
      "flags": flags,
    })
  return rows


def main() -> None:
  if len(sys.argv) != 3:
    fail(f"usage: {pathlib.Path(sys.argv[0]).name} <firmware.zip> <layout.json>")

  fw_path = pathlib.Path(sys.argv[1])
  layout_path = pathlib.Path(sys.argv[2])
  expected = json.loads(layout_path.read_text(encoding="utf-8"))
  fw_bytes = fw_path.read_bytes()
  if sha256(fw_bytes).lower() != expected["package_sha256"].lower():
    fail("firmware package SHA-256 differs from the pinned PlugMG3 package")

  with zipfile.ZipFile(fw_path, "r") as archive:
    names = set(archive.namelist())
    required = {"manifest.json", "bootloader.bin", "partition-table.bin", "boot_state.bin", "PlugMG3.bin", "fs.img"}
    missing = sorted(required - names)
    if missing:
      fail(f"firmware ZIP is missing: {', '.join(missing)}")

    manifest = json.loads(archive.read("manifest.json"))
    for key in ("name", "platform", "version", "build_id"):
      if manifest.get(key) != expected.get(key):
        fail(f"manifest {key}={manifest.get(key)!r}, expected {expected.get(key)!r}")

    if manifest.get("parts", {}).get("pt", {}).get("addr") != expected["partition_table"]["offset"]:
      fail("partition-table address differs from confirmed layout")
    if manifest.get("parts", {}).get("boot", {}).get("addr") != expected["bootloader"]["offset"]:
      fail("bootloader address differs from confirmed layout")

    checks = (
      ("bootloader.bin", expected["bootloader"]["sha256"]),
      ("partition-table.bin", expected["partition_table"]["sha256"]),
      ("boot_state.bin", expected["parts"]["otadata"]["sha256"]),
      ("PlugMG3.bin", expected["parts"]["app"]["sha256"]),
      ("fs.img", expected["parts"]["fs"]["sha256"]),
    )
    for name, digest in checks:
      actual = sha256(archive.read(name))
      if actual.lower() != digest.lower():
        fail(f"{name} SHA-256 differs from confirmed layout")

    actual_partitions = parse_partition_table(archive.read("partition-table.bin"))
    if actual_partitions != expected["partitions"]:
      fail("partition table differs from pinned PlugMG3 layout")

  print("Pinned PlugMG3 package and partition layout: OK")


if __name__ == "__main__":
  main()
