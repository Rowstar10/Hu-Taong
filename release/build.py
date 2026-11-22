"""Build one version of Hu Taong for Windows, and zip it.

    python release/build.py --source <that version's files> --version 1.9 [--out dist]

Makes <out>/Hu Taong/ (Hu Taong.exe and its _internal folder) and <out>/Hu-Taong-1.9-windows.zip,
whose one top folder is "Hu Taong". It works on any version's source, from 0.1 (Tkinter) on, and
needs PyInstaller, and pygame 2.6.1 for 0.5 on, in the Python that runs it (release.py sets that
up). Toki Hub installs the zip; anyone can also unzip it and run Hu Taong.exe.
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
NAME = "Hu Taong"
# Already compressed: zipping them again only takes time
STORED = {".mp3", ".ogg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".ico", ".pyd", ".dll", ".exe", ".zip"}


def zip_name(version):
    return f"Hu-Taong-{version}-windows.zip"


def entry_point(source):
    """The version's main script: main.py from 0.3 on, HuTaong_Tkinter_v0.x.py before."""
    if (source / "main.py").exists():
        return "main.py"
    scripts = sorted(source.glob("HuTaong_Tkinter_v*.py"))
    if scripts:
        return scripts[0].name
    raise SystemExit(f"Hu Taong's main script isn't in {source}")


def uses_tkinter(source):
    """0.1 to 0.4 are drawn with Tkinter; 0.5 on with pygame."""
    code = [p.read_text(encoding="utf-8", errors="ignore") for p in source.rglob("*.py")
            if "tests" not in p.parts and ".git" not in p.parts]
    return not any("import pygame" in text for text in code) and any("tkinter" in text for text in code)


def build(source, version, out):
    source, out = Path(source).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    app = out / NAME
    if app.exists():
        shutil.rmtree(app)
    entry, tk = entry_point(source), uses_tkinter(source)
    print(f"Building Hu Taong {version} from {source} ({entry}, {'Tkinter' if tk else 'pygame'})", flush=True)
    env = dict(os.environ, HUTAONG_SOURCE=str(source), HUTAONG_ENTRY=entry, HUTAONG_TK="1" if tk else "0",
               PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE="1")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
                    "--distpath", str(out), "--workpath", str(out / "pyinstaller-work"),
                    str(HERE / "hu_taong.spec")], check=True, env=env, cwd=source)
    exe = app / (NAME + (".exe" if os.name == "nt" else ""))
    if not exe.exists():
        raise SystemExit(f"PyInstaller finished, but {exe} isn't there")
    if not (app / "_internal" / "Resources").is_dir() and (source / "Resources").is_dir():
        raise SystemExit("The build has no Resources folder: the game's pictures and sounds are missing")
    return pack(app, out / zip_name(version))


def pack(app, zip_path):
    """Zip the build folder (as "Hu Taong/..."), check the zip reads back, and say its sha256."""
    tmp = zip_path.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w") as archive:
        for path in sorted(app.rglob("*")):
            if path.is_file():
                arcname = Path(NAME, path.relative_to(app)).as_posix()
                method = zipfile.ZIP_STORED if path.suffix.lower() in STORED else zipfile.ZIP_DEFLATED
                archive.write(path, arcname, compress_type=method)
    with zipfile.ZipFile(tmp) as archive:
        broken = archive.testzip()
        if broken:
            raise SystemExit(f"The zip came out damaged ({broken}); try again")
    tmp.replace(zip_path)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    print(f"Made {zip_path.name}: {zip_path.stat().st_size / 1e6:.0f} MB, sha256 {digest}", flush=True)
    return zip_path


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--source", required=True, help="that version's files")
    parser.add_argument("--version", required=True, help="like 1.9")
    parser.add_argument("--out", default="dist", help="where the build and zip go (default: dist)")
    args = parser.parse_args()
    build(args.source, args.version, args.out)


if __name__ == "__main__":
    main()
