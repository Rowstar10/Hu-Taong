"""Publish a version of Hu Taong for your friends: build it and put it on the public releases repo,
where Toki Hub finds it. Run it on your Windows PC from this folder:

    py release.py 1.10                  build 1.10 and publish it
    py release.py 1.10 --no-publish     only build the zip (in dist), to try it first
    py release.py 1.5 --ref 0e742ec     build a commit other than the version's tag

What it does:
  1. Checks the GitHub CLI is there and signed in (it publishes as you: no token is stored).
  2. Copies the version's committed files (its tag, v1.10) into a clean folder, so nothing
     half-finished in this folder gets in.
  3. Builds the Windows version and zips it: dist/Hu-Taong-1.10-windows.zip (release/build.py),
     with its own Python setup in .release-venv.
  4. Has GitHub build and test the Android APK for that version, and downloads it.
  5. Publishes both as release v1.10 of the releases repo, with the version's CHANGELOG.md
     section as its notes.
"""
import argparse
import calendar
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

# The public repo that holds the builds (Toki Hub's catalog points at the same one)
RELEASES_REPO = "Rowstar10/Hu-Taong-Releases"
ANDROID_WORKFLOW = "android.yml"
ANDROID_ARTIFACT = "Hu-Taong-android"
PYTHON = (3, 12)

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".release-venv"
WORK = ROOT / ".release-work"
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT / "release"))
import build  # noqa: E402  (release/build.py)


def say(text):
    print(f"\n== {text}", flush=True)


def stop(text):
    print(f"\nRelease stopped: {text}", flush=True)
    sys.exit(1)


def run(*args, capture=False, check=True, cwd=ROOT):
    result = subprocess.run(args, cwd=cwd, text=True, capture_output=capture)
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        stop(f"{' '.join(map(str, args[:3]))} ... failed{': ' + detail if detail else ''}")
    return result.stdout.strip() if capture else result


def version_key(version):
    return tuple(int(part) for part in re.findall(r"\d+", version))


# ---------- 1. GitHub CLI ----------

def check_gh(source_repo):
    if not shutil.which("gh"):
        stop("the GitHub CLI isn't installed. Get it from https://cli.github.com, then run "
             "'gh auth login' once, and try again.")
    if subprocess.run(["gh", "auth", "status"], capture_output=True).returncode != 0:
        stop("the GitHub CLI isn't signed in. Run 'gh auth login' once, then try again.")
    for repo in (RELEASES_REPO, source_repo):
        if subprocess.run(["gh", "repo", "view", repo], capture_output=True).returncode != 0:
            stop(f"can't see the repo {repo} with your GitHub login (does it exist?)")


def source_repo():
    """owner/name of this folder's GitHub repo, from its origin remote."""
    url = run("git", "remote", "get-url", "origin", capture=True)
    found = re.search(r"github\.com[:/]+([^/]+/[^/.]+)", url)
    if not found:
        stop(f"this folder's git origin ({url}) isn't on GitHub")
    return found.group(1)


# ---------- 2. The version's files ----------

def resolve(version, ref):
    """The commit to build: --ref, or the version's tag (made and pushed now if you agree)."""
    tag = f"v{version}"
    run("git", "fetch", "--quiet", "--tags", "--force", "origin")    # (a tag moved on GitHub wins)
    if ref:
        return run("git", "rev-parse", f"{ref}^{{commit}}", capture=True), tag
    if subprocess.run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], cwd=ROOT,
                      capture_output=True).returncode == 0:
        return run("git", "rev-parse", f"{tag}^{{commit}}", capture=True), tag
    head = run("git", "log", "-1", "--format=%h %s", capture=True)
    answer = input(f"There's no tag {tag} yet. Tag your latest commit ({head}) as {tag} and push it? [y/N] ")
    if answer.strip().lower() not in ("y", "yes"):
        stop(f"tag the commit for {version} first: git tag {tag} <commit>, then git push origin {tag}")
    run("git", "tag", tag)
    run("git", "push", "origin", tag)
    return run("git", "rev-parse", "HEAD", capture=True), tag


def checkout(commit, version):
    folder = WORK / version
    if folder.exists():
        subprocess.run(["git", "worktree", "remove", "--force", str(folder)], cwd=ROOT, capture_output=True)
        shutil.rmtree(folder, ignore_errors=True)
    run("git", "worktree", "prune")
    run("git", "worktree", "add", "--detach", "--quiet", str(folder), commit)
    return folder


def drop_checkout(folder):
    subprocess.run(["git", "worktree", "remove", "--force", str(folder)], cwd=ROOT, capture_output=True)
    shutil.rmtree(folder, ignore_errors=True)
    subprocess.run(["git", "worktree", "prune"], cwd=ROOT, capture_output=True)


# ---------- 3. The Windows build ----------

def venv_python():
    """.release-venv's Python, made the first time with Python 3.12 and the build tools."""
    python = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        say("Setting up the build tools (only the first time)")
        if sys.version_info[:2] == PYTHON:
            maker = [sys.executable]
        elif os.name == "nt" and shutil.which("py"):
            maker = ["py", f"-{PYTHON[0]}.{PYTHON[1]}"]
        else:
            stop(f"Python {PYTHON[0]}.{PYTHON[1]} is needed to build. Install it from python.org and try again.")
        run(*maker, "-m", "venv", str(VENV))
    run(str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r",
        str(ROOT / "release" / "requirements.txt"))
    return python


def build_windows(python, source, version):
    say(f"Building Hu Taong {version} for Windows")
    run(str(python), str(ROOT / "release" / "build.py"), "--source", str(source), "--version", version,
        "--out", str(DIST))
    return DIST / build.zip_name(version)


# ---------- 4. The Android APK ----------

def build_android(repo, tag, commit, version):
    """Run the Android workflow (GitHub builds the APK and plays it on an emulated phone), wait for
    it, and download the APK. None for versions from before the phone version (1.5)."""
    if subprocess.run(["git", "cat-file", "-e", f"{commit}:core/platform.py"], cwd=ROOT,
                      capture_output=True).returncode != 0:
        print("(no Android version: it came with 1.5)")
        return None
    say(f"GitHub is building and testing the Android APK for {version} (about 30 to 60 minutes)")
    started = time.time()
    run("gh", "workflow", "run", ANDROID_WORKFLOW, "--repo", repo, "--ref", "main", "-f", f"tag={tag}", "-f", f"ref={commit}")
    run_id = None
    for _ in range(30):
        time.sleep(5)
        runs = json.loads(run("gh", "run", "list", "--repo", repo, "--workflow", ANDROID_WORKFLOW, "--event",
                              "workflow_dispatch", "--limit", "5", "--json", "databaseId,createdAt", capture=True))
        fresh = [r for r in runs if calendar.timegm(time.strptime(r["createdAt"], "%Y-%m-%dT%H:%M:%SZ")) >= started - 60]
        if fresh:
            run_id = str(fresh[0]["databaseId"])
            break
    if not run_id:
        stop("GitHub didn't start the Android build. See the Actions tab of the source repo.")
    print(f"https://github.com/{repo}/actions/runs/{run_id}")
    if subprocess.run(["gh", "run", "watch", run_id, "--repo", repo, "--exit-status", "--interval", "30"],
                      cwd=ROOT).returncode != 0:
        stop(f"the Android build or its test failed: https://github.com/{repo}/actions/runs/{run_id}")
    target = DIST / "android"
    shutil.rmtree(target, ignore_errors=True)
    run("gh", "run", "download", run_id, "--repo", repo, "--name", ANDROID_ARTIFACT, "--dir", str(target))
    apks = sorted(target.glob("*.apk"))
    if not apks:
        stop("the Android build finished but its APK wasn't in it")
    apk = DIST / apks[0].name
    shutil.move(str(apks[0]), apk)
    return apk


# ---------- 5. Publishing ----------

def notes(commit, version):
    """The version's section of its CHANGELOG.md, then how to install it."""
    changelog = subprocess.run(["git", "show", f"{commit}:CHANGELOG.md"], cwd=ROOT, capture_output=True,
                               text=True, encoding="utf-8").stdout
    section, inside = [], False
    for line in changelog.splitlines():
        if line.startswith("## "):
            words = line[3:].split()
            inside = bool(words) and words[0].strip("[]").lstrip("vV") == version
            continue
        if inside:
            section.append(line)
    text = "\n".join(section).strip() or f"Hu Taong {version}."
    return (text + f"\n\nInstall it from Toki Hub. Or download {build.zip_name(version)}, unzip it and "
            "run Hu Taong.exe; on Android, download the APK and open it.\n")


def publish(tag, version, files, commit):
    say(f"Publishing {tag} on {RELEASES_REPO}")
    existing = json.loads(run("gh", "release", "list", "--repo", RELEASES_REPO, "--limit", "200", "--json",
                              "tagName", capture=True) or "[]")
    tags = [r["tagName"] for r in existing]
    if tag in tags:
        run("gh", "release", "upload", tag, *map(str, files), "--repo", RELEASES_REPO, "--clobber")
    else:
        newest = all(version_key(version) >= version_key(t) for t in tags)
        notes_file = DIST / f"notes-{version}.md"
        notes_file.write_text(notes(commit, version), encoding="utf-8")
        run("gh", "release", "create", tag, *map(str, files), "--repo", RELEASES_REPO, "--title",
            f"Hu Taong {version}", "--notes-file", str(notes_file), f"--latest={'true' if newest else 'false'}")
    print(f"https://github.com/{RELEASES_REPO}/releases/tag/{tag}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", help="the version to release, like 1.10")
    parser.add_argument("--ref", help="the commit to build (default: the version's tag, v<version>)")
    parser.add_argument("--no-publish", action="store_true", help="only build the Windows zip, in dist")
    parser.add_argument("--no-android", action="store_true", help="publish without the Android APK")
    args = parser.parse_args()
    version = args.version.lstrip("vV")
    if not re.fullmatch(r"\d+(\.\d+)*", version):
        stop(f"{args.version} isn't a version number like 1.10")

    repo = source_repo()
    if not args.no_publish:
        check_gh(repo)
    commit, tag = resolve(version, args.ref)
    say(f"Hu Taong {version}: {tag}, commit {commit[:10]}")
    source = checkout(commit, version)
    try:
        zip_path = build_windows(venv_python(), source, version)
    finally:
        drop_checkout(source)
    if args.no_publish:
        say(f"Built {zip_path} (not published). Unzip it and run Hu Taong.exe to try it.")
        return
    files = [zip_path]
    if not args.no_android:
        apk = build_android(repo, tag, commit, version)
        if apk:
            files.append(apk)
    publish(tag, version, files, commit)
    say(f"Hu Taong {version} is out. Toki Hub lists it the next time it checks (or press reload).")


if __name__ == "__main__":
    main()
