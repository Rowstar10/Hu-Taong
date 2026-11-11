"""Gathers what the Android APK needs into one folder (android/build.sh packs that folder).

The game's code and Resources, less what a phone never uses (the tests, the server, the .exe's
icon, files the game doesn't load), with two changes for a phone:

- The music is re-encoded at a phone's bitrate (about 112 kbps, from up to 320).  It's about
  half of a 250 MB game, and a phone unpacks the game once more on first launch, so this
  keeps the APK and the space it takes small.  It needs ffmpeg (on the PATH, or pip's
  imageio-ffmpeg); without it the music goes in as it is.
- A start-up picture (presplash.jpg) and an icon (icon.png) for Android, beside the folder.

    python android/stage.py <out folder>
"""
import json, os, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

GAME = Path(__file__).resolve().parent.parent
CODE = ["main.py", "config.py", "helpers.py", "core", "game", "objects", "render"]
UNUSED = {            # as main.spec: files in Resources the game never loads
    "Images/craig-cyrax-hu-tao-22.jpg",
    "Images/Hu-Tao-Ghost-Landscape.jpg",
    "Images/tst,small,507x507-pad,600x600,f8f8f8.webp",
    "Images/icon.ico",
    "Sounds/you_win2.wav",
    "Sounds/Music/you_win.wav",
}
MUSIC_KBPS = 112


def copy_code(out):
    for name in CODE:
        src = GAME / name
        if src.is_dir():
            shutil.copytree(src, out / name, ignore = shutil.ignore_patterns("__pycache__", "*.pyc"))
        else:
            shutil.copy2(src, out / name)


def ffmpeg():
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG = ffmpeg()


def shrink(src, dst):
    """A track at a phone's bitrate; True if ffmpeg made it smaller."""
    if not FFMPEG:
        return False
    tmp = dst.with_name(dst.stem + ".tmp" + dst.suffix)
    codec = ["-c:a", "libmp3lame", "-b:a", f"{MUSIC_KBPS}k"] if src.suffix == ".mp3" else \
            ["-c:a", "libvorbis", "-b:a", f"{MUSIC_KBPS}k"]
    done = subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-map", "0:a", "-map_metadata", "-1",
                           *codec, str(tmp)], capture_output = True)
    if done.returncode != 0 or not tmp.exists() or tmp.stat().st_size >= src.stat().st_size:
        tmp.unlink(missing_ok = True)
        return False
    tmp.replace(dst)
    return True


def copy_resources(out):
    root = GAME / "Resources"
    tracks = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or rel in UNUSED:
            continue
        dst = out / "Resources" / rel
        dst.parent.mkdir(parents = True, exist_ok = True)
        if rel.startswith("Sounds/Music/") and path.suffix in (".mp3", ".ogg"):
            tracks.append((path, dst))
        else:
            shutil.copy2(path, dst)

    def track(job):
        src, dst = job
        if not shrink(src, dst):
            shutil.copy2(src, dst)
        return src.stat().st_size, dst.stat().st_size

    with ThreadPoolExecutor(max_workers = os.cpu_count() or 2) as pool:      # one ffmpeg per core
        sizes = list(pool.map(track, tracks))
    print(f"music: {sum(a for a, _ in sizes) / 1e6:.0f} MB -> {sum(b for _, b in sizes) / 1e6:.0f} MB")


def make_pictures(out):
    """Android's start-up picture and launcher icon, from the game's own."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    art = GAME / "Resources" / "Images"
    picture = pygame.image.load(str(art / "Hu-Tao-Ghost-Landscape.jpg"))
    w, h = picture.get_size()
    scale = 1280 / w
    picture = pygame.transform.smoothscale(picture, (1280, round(h * scale)))
    pygame.image.save(picture, str(out.parent / "presplash.jpg"))
    icon = pygame.transform.smoothscale(pygame.image.load(str(art / "icon.png")), (512, 512))
    pygame.image.save(icon, str(out.parent / "icon.png"))


def main():
    out = Path(sys.argv[1]).resolve()
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents = True)
    copy_code(out)
    copy_resources(out)
    make_pictures(out)
    (out.parent / "stage.json").write_text(json.dumps({"files": sum(1 for p in out.rglob("*") if p.is_file())}))


if __name__ == "__main__":
    main()
