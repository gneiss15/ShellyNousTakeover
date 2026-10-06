#!/usr/bin/env python3
# DeviceTypeArtifacts.py, Version: 1.02

from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import re
import struct
import subprocess


MAGIC = b"ESPDT01\0"
HEADER_SIZE = 64
FORMAT_VERSION = 1
MAX_DEVICE_TYPE_LENGTH = 31
ARTIFACT_TYPES = {
  "firmware": 1,
  "filesystem": 2,
  "combined": 3,
  "config": 4,
  "rescue": 5,
}
SIGNATURE_MAGIC = b"ESPSIG01"
SIGNATURE_HEADER_SIZE = 48
SIGNATURE_FORMAT_VERSION = 1
SIGNATURE_HASH_SHA256 = 1


def Fail(Message: str) -> None:
  raise SystemExit(f"Error: {Message}")


def ReadDeviceType(FileName: Path) -> str:
  if not FileName.is_file():
    Fail(f"Device type file not found: {FileName}")

  Lines = [
    Line.strip()
    for Line in FileName.read_text(encoding="utf-8").splitlines()
    if Line.strip() and not Line.strip().startswith("//")
  ]
  if len(Lines) != 1:
    Fail(f"Device type file must contain exactly one id: {FileName}")
  DeviceType = Lines[0]
  if len(DeviceType.encode("ascii", errors="ignore")) != len(DeviceType):
    Fail("Device type must contain ASCII characters only")
  if len(DeviceType) > MAX_DEVICE_TYPE_LENGTH:
    Fail(f"Device type is too long: {len(DeviceType)} > {MAX_DEVICE_TYPE_LENGTH}")
  if not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", DeviceType):
    Fail("Device type must match [A-Za-z][A-Za-z0-9]*")
  return DeviceType


def WritePreparedFiles(DeviceTypeFile: Path, HeaderFile: Path, DataFile: Path) -> None:
  DeviceType = ReadDeviceType(DeviceTypeFile)

  HeaderFile.parent.mkdir(parents=True, exist_ok=True)
  HeaderFile.write_text(
    "// DeviceType.inc.h, Version: 1.00\n"
    "#pragma once\n\n"
    f'#define ESP_UPDATE_DEVICE_TYPE "{DeviceType}"\n',
    encoding="utf-8",
  )

  DataFile.parent.mkdir(parents=True, exist_ok=True)
  DataFile.write_text(DeviceType + "\n", encoding="ascii")


def WriteArtifact(DeviceTypeFile: Path, ArtifactType: str,
                  InputFile: Path, OutputFile: Path) -> None:
  DeviceType = ReadDeviceType(DeviceTypeFile)
  if ArtifactType not in ARTIFACT_TYPES:
    Fail(f"Unknown artifact type: {ArtifactType}")
  if not InputFile.is_file():
    Fail(f"Input file not found: {InputFile}")

  Payload = InputFile.read_bytes()
  if not Payload:
    Fail(f"Input file is empty: {InputFile}")
  if len(Payload) > 0xFFFFFFFF:
    Fail("Input file is too large")

  DeviceTypeBytes = DeviceType.encode("ascii") + b"\0"
  DeviceTypeField = DeviceTypeBytes.ljust(32, b"\0")
  Header = struct.pack(
    "<8sHBBI32s16s",
    MAGIC,
    HEADER_SIZE,
    FORMAT_VERSION,
    ARTIFACT_TYPES[ArtifactType],
    len(Payload),
    DeviceTypeField,
    b"\0" * 16,
  )
  if len(Header) != HEADER_SIZE:
    Fail("Internal header size mismatch")

  OutputFile.parent.mkdir(parents=True, exist_ok=True)
  OutputFile.write_bytes(Header + Payload)



def ReadArtifactHeader(Data: bytes) -> tuple[int, int, str]:
  if len(Data) < HEADER_SIZE:
    Fail("Artifact is too short")
  Magic, HeaderSize, FormatVersion, ArtifactType, PayloadSize, DeviceTypeRaw, Reserved = struct.unpack(
    "<8sHBBI32s16s", Data[:HEADER_SIZE]
  )
  if Magic != MAGIC or HeaderSize != HEADER_SIZE or FormatVersion != FORMAT_VERSION:
    Fail("Invalid DeviceType artifact header")
  if any(Reserved):
    Fail("Unsupported DeviceType artifact header extension")
  DeviceType = DeviceTypeRaw.split(b"\0", 1)[0].decode("ascii")
  if not DeviceType or PayloadSize == 0:
    Fail("Invalid DeviceType artifact metadata")
  return ArtifactType, PayloadSize, DeviceType


def SignArtifact(InputFile: Path, PrivateKey: Path, OutputFile: Path) -> None:
  if not InputFile.is_file():
    Fail(f"Input file not found: {InputFile}")
  if not PrivateKey.is_file():
    Fail(f"Private key not found: {PrivateKey}")

  Data = InputFile.read_bytes()
  _, PayloadSize, _ = ReadArtifactHeader(Data)
  Payload = Data[HEADER_SIZE:]
  if len(Payload) != PayloadSize:
    Fail("DeviceType artifact payload size mismatch")
  PayloadHash = hashlib.sha256(Payload).digest()

  SignatureSize = 0
  for _ in range(2):
    SignatureHeader = struct.pack(
      "<8sHBBI32s", SIGNATURE_MAGIC, SIGNATURE_HEADER_SIZE,
      SIGNATURE_FORMAT_VERSION, SIGNATURE_HASH_SHA256, SignatureSize, PayloadHash
    )
    Manifest = Data[:HEADER_SIZE] + SignatureHeader
    Result = subprocess.run(
      ["openssl", "dgst", "-sha256", "-sign", str(PrivateKey)],
      input=Manifest, capture_output=True
    )
    if Result.returncode != 0 or not Result.stdout:
      Fail("OpenSSL signing failed")
    if SignatureSize == len(Result.stdout):
      Signature = Result.stdout
      break
    SignatureSize = len(Result.stdout)
  else:
    Fail("Could not determine stable signature size")

  OutputFile.parent.mkdir(parents=True, exist_ok=True)
  OutputFile.write_bytes(Manifest + Signature + Payload)


def VerifySignedArtifact(InputFile: Path, PublicKey: Path) -> None:
  if not InputFile.is_file():
    Fail(f"Signed artifact not found: {InputFile}")
  if not PublicKey.is_file():
    Fail(f"Public key not found: {PublicKey}")
  Data = InputFile.read_bytes()
  if len(Data) < HEADER_SIZE + SIGNATURE_HEADER_SIZE:
    Fail("Signed artifact is too short")
  _, PayloadSize, _ = ReadArtifactHeader(Data)
  SigMagic, SigHeaderSize, SigVersion, HashType, SignatureSize, PayloadHash = struct.unpack(
    "<8sHBBI32s", Data[HEADER_SIZE:HEADER_SIZE + SIGNATURE_HEADER_SIZE]
  )
  if SigMagic != SIGNATURE_MAGIC or SigHeaderSize != SIGNATURE_HEADER_SIZE or \
     SigVersion != SIGNATURE_FORMAT_VERSION or HashType != SIGNATURE_HASH_SHA256 or SignatureSize == 0:
    Fail("Invalid signed-artifact header")
  PayloadOffset = HEADER_SIZE + SIGNATURE_HEADER_SIZE + SignatureSize
  if PayloadOffset + PayloadSize != len(Data):
    Fail("Signed artifact size mismatch")
  Signature = Data[HEADER_SIZE + SIGNATURE_HEADER_SIZE:PayloadOffset]
  Payload = Data[PayloadOffset:]
  if hashlib.sha256(Payload).digest() != PayloadHash:
    Fail("Signed artifact payload hash mismatch")
  Manifest = Data[:HEADER_SIZE + SIGNATURE_HEADER_SIZE]
  # OpenSSL needs separate signature and manifest files for verification.
  import tempfile
  with tempfile.TemporaryDirectory() as TempDir:
    Temp = Path(TempDir)
    ManifestFile = Temp / "manifest.bin"
    SignatureFile = Temp / "signature.bin"
    ManifestFile.write_bytes(Manifest)
    SignatureFile.write_bytes(Signature)
    Result = subprocess.run(
      ["openssl", "dgst", "-sha256", "-verify", str(PublicKey),
       "-signature", str(SignatureFile), str(ManifestFile)],
      capture_output=True
    )
    if Result.returncode != 0:
      Fail("RSA signature verification failed")


def WritePublicKeyHeader(PublicKey: Path, OutputFile: Path) -> None:
  if not PublicKey.is_file():
    Fail(f"Public key not found: {PublicKey}")
  Result = subprocess.run(
    ["openssl", "pkey", "-pubin", "-in", str(PublicKey), "-outform", "DER"],
    capture_output=True
  )
  if Result.returncode != 0 or not Result.stdout:
    Fail("Could not convert public key to DER")
  Data = Result.stdout
  Lines = []
  for Offset in range(0, len(Data), 16):
    Lines.append("  " + ", ".join(f"0x{Value:02X}" for Value in Data[Offset:Offset + 16]))
  OutputFile.parent.mkdir(parents=True, exist_ok=True)
  OutputFile.write_text(
    "// EspUpdatePublicKey.h, Version: 1.00\n#pragma once\n\n"
    "#include <cstddef>\n#include <cstdint>\n\n"
    "namespace EspUpdatePublicKey\n {\n"
    "constexpr uint8_t Data[] =\n {\n" + ",\n".join(Lines) + "\n };\n"
    "constexpr size_t Size = sizeof( Data );\n }\n",
    encoding="utf-8"
  )

def ParseArgs() -> argparse.Namespace:
  Parser = argparse.ArgumentParser(description="Prepare and wrap DeviceType OTA artifacts")
  SubParsers = Parser.add_subparsers(dest="Command", required=True)

  PrepareParser = SubParsers.add_parser("prepare")
  PrepareParser.add_argument("DeviceTypeFile", type=Path)
  PrepareParser.add_argument("HeaderFile", type=Path)
  PrepareParser.add_argument("DataFile", type=Path)

  WrapParser = SubParsers.add_parser("wrap")
  WrapParser.add_argument("DeviceTypeFile", type=Path)
  WrapParser.add_argument("ArtifactType", choices=tuple(ARTIFACT_TYPES))
  WrapParser.add_argument("InputFile", type=Path)
  WrapParser.add_argument("OutputFile", type=Path)

  SignParser = SubParsers.add_parser("sign")
  SignParser.add_argument("InputFile", type=Path)
  SignParser.add_argument("PrivateKey", type=Path)
  SignParser.add_argument("OutputFile", type=Path)

  VerifyParser = SubParsers.add_parser("verify")
  VerifyParser.add_argument("InputFile", type=Path)
  VerifyParser.add_argument("PublicKey", type=Path)

  KeyParser = SubParsers.add_parser("public-key-header")
  KeyParser.add_argument("PublicKey", type=Path)
  KeyParser.add_argument("OutputFile", type=Path)

  return Parser.parse_args()


def Main() -> None:
  Args = ParseArgs()
  if Args.Command == "prepare":
    WritePreparedFiles(Args.DeviceTypeFile, Args.HeaderFile, Args.DataFile)
  elif Args.Command == "wrap":
    WriteArtifact(Args.DeviceTypeFile, Args.ArtifactType, Args.InputFile, Args.OutputFile)
  elif Args.Command == "sign":
    SignArtifact(Args.InputFile, Args.PrivateKey, Args.OutputFile)
  elif Args.Command == "verify":
    VerifySignedArtifact(Args.InputFile, Args.PublicKey)
  elif Args.Command == "public-key-header":
    WritePublicKeyHeader(Args.PublicKey, Args.OutputFile)


if __name__ == "__main__":
  Main()
