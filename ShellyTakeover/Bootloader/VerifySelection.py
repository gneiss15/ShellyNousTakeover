# VerifySelection.py, Version: 1.02
import ctypes
import pathlib
import subprocess
import tempfile
import zlib

root = pathlib.Path(__file__).resolve().parent
shared = root / "bootloader_components"
def synthetic_record():
    data = bytearray(512)
    data[:4] = data[12:16] = (10).to_bytes(4, 'little')
    data[8:12] = b'SH0S'
    data[0x1d0:0x1d2] = bytes([0x12, 0x20])
    data[28:32] = zlib.crc32(bytes(4), zlib.crc32(data[:28], 0xffffffff)).to_bytes(4, 'little')
    data[508:512] = zlib.crc32(data[:508], 0xffffffff).to_bytes(4, 'little')
    return bytes(data)

with tempfile.TemporaryDirectory() as work:
    library = pathlib.Path(work) / "selection.so"
    subprocess.run(["cc", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
                    "-I", str(shared / "main"),
                    str(root / "bootloader_components/main/Selection.c"),
                    str(shared / "main/BootState.c"), "-o", str(library)], check=True)
    api = ctypes.CDLL(str(library))
    api.SelectStockLayoutApp.argtypes = [ctypes.c_bool, ctypes.c_void_p]
    api.SelectStockLayoutApp.restype = ctypes.c_int

    def record(active, committed, mfs=2, sequence=10):
        data = bytearray(synthetic_record())
        data.extend(bytes([0xff]) * (4096 - len(data)))
        assert len(data) == 4096
        data[0:4] = data[12:16] = sequence.to_bytes(4, "little")
        data[0x1d0] = (active << 4) | committed
        data[0x1d1] = (mfs << 4) | (1 - active)
        data[28:32] = zlib.crc32(bytes(4), zlib.crc32(data[:28], 0xffffffff)).to_bytes(4, "little")
        data[508:512] = zlib.crc32(data[:508], 0xffffffff).to_bytes(4, "little")
        return data

    count = 0

    def check(data, expected):
        global count
        buffer = ctypes.create_string_buffer(bytes(data))
        before = buffer.raw
        assert api.SelectStockLayoutApp(False, buffer) == expected
        assert api.SelectStockLayoutApp(True, buffer) == 0
        assert buffer.raw == before, "Selection modified metadata"
        count += 1

    for active, committed, expected in [(1, 0, 1), (1, 1, 1), (0, 1, 0), (0, 0, 0)]:
        for mfs in (0, 1, 2):
            item = record(active, committed, mfs)
            check(item + item, expected)
    stock = record(0, 1, sequence=11)
    own = record(1, 0, sequence=10)
    check(own + stock, 0)
    check(stock + own, 0)
    check(bytes(4096) + own, 1)
    check(own + bytes(4096), 1)
    check(bytes(8192), 0)
    check(record(0, 1) + own, 0)  # Equal sequence, conflicting valid records.
    bad = bytearray(own)
    bad[100] ^= 1
    check(bad + bad, 0)
    assert api.SelectStockLayoutApp(False, None) == 0
    print(f"Selection: {count} metadata cases, key override and no-write checks passed")
