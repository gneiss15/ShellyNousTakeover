#!/usr/bin/env python3
# ServeFirmware.py, Version: 1.01

import argparse
import http.server
import pathlib
import socketserver
import sys
from urllib.parse import unquote, urlsplit


class FirmwareHandler(http.server.BaseHTTPRequestHandler):
  server_version = "ShellyTakeoverFirmwareServer/1.01"

  def log_message(self, fmt, *args):
    sys.stdout.write("HTTP %s - %s\n" % (self.address_string(), fmt % args))
    sys.stdout.flush()

  def _resolve_request(self):
    path = unquote(urlsplit(self.path).path)
    if path != "/" + self.server.firmware_path.name:
      self.send_error(404)
      return None
    return self.server.firmware_path

  def _send_headers(self, file_path):
    size = file_path.stat().st_size
    self.send_response(200)
    self.send_header("Content-Type", "application/zip")
    self.send_header("Content-Length", str(size))
    self.send_header("Cache-Control", "no-store")
    self.end_headers()
    return size

  def do_HEAD(self):
    file_path = self._resolve_request()
    if file_path is None:
      return
    size = self._send_headers(file_path)
    print(f"HEAD_COMPLETE client={self.client_address[0]} bytes={size}", flush=True)

  def do_GET(self):
    file_path = self._resolve_request()
    if file_path is None:
      return

    size = self._send_headers(file_path)
    sent = 0
    try:
      with file_path.open("rb") as f:
        while True:
          chunk = f.read(64 * 1024)
          if not chunk:
            break
          self.wfile.write(chunk)
          sent += len(chunk)
      self.wfile.flush()
    except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as exc:
      print(
        f"GET_INCOMPLETE client={self.client_address[0]} bytes={sent}/{size} error={type(exc).__name__}",
        flush=True,
      )
      return

    print(f"GET_COMPLETE client={self.client_address[0]} bytes={sent}/{size}", flush=True)


class FirmwareServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
  daemon_threads = True
  allow_reuse_address = True

  def __init__(self, server_address, handler_class, firmware_path):
    super().__init__(server_address, handler_class)
    self.firmware_path = firmware_path


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--bind", required=True)
  parser.add_argument("--port", required=True, type=int)
  parser.add_argument("--file", required=True)
  args = parser.parse_args()

  firmware_path = pathlib.Path(args.file).resolve()
  if not firmware_path.is_file():
    raise SystemExit(f"Firmware file not found: {firmware_path}")

  with FirmwareServer((args.bind, args.port), FirmwareHandler, firmware_path) as server:
    print(
      f"SERVER_READY bind={args.bind} port={server.server_address[1]} file={firmware_path.name} bytes={firmware_path.stat().st_size}",
      flush=True,
    )
    server.serve_forever(poll_interval=0.2)


if __name__ == "__main__":
  main()
