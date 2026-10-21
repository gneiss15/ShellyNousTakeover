# BuildFiles.py, Version: 1.01
"""Keep this standalone project's generated build inputs stable when unchanged."""
from pathlib import Path
import shutil


def write_bytes_if_changed(path, content):
    path=Path(path)
    if path.is_file() and path.read_bytes()==content:return False
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(content)
    return True


def write_text_if_changed(path, content, encoding='utf-8'):
    return write_bytes_if_changed(path,content.encode(encoding))


def copy_file_if_changed(source, target):
    changed=write_bytes_if_changed(target,Path(source).read_bytes())
    if changed:shutil.copymode(source,target)
    return changed


def generate_output_if_changed(command, padding=0):
  """Stage a generator's final output before publishing its finished bytes."""
  import tempfile
  import subprocess
  output = Path(command[-1])
  output.parent.mkdir(parents=True, exist_ok=True)
  stage = Path(tempfile.mkdtemp(prefix=".generator-", dir=output.parent))
  temporary = stage / output.name
  try:
    subprocess.run([*command[:-1], str(temporary)], check=True)
    data = temporary.read_bytes()
    if padding:
      data = data.ljust(padding, b"\xff")
    return write_bytes_if_changed(output, data)
  finally:
    shutil.rmtree(stage)


if __name__=='__main__':
    import sys
    copy_file_if_changed(sys.argv[1],sys.argv[2])
