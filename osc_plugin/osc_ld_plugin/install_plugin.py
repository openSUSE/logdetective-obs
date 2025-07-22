import shutil
from pathlib import Path

def main():
    dest_dir = Path.home() / ".osc-plugins"
    dest_dir.mkdir(parents=True, exist_ok=True)

    src_file = Path(__file__).parent / "plugin.py"
    dest_file = dest_dir / "ld.py"

    shutil.copy2(src_file, dest_file)
    print(f"✅ Installed osc plugin to: {dest_file}")
