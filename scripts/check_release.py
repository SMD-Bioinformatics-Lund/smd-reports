"""Check a release tag, master ancestry and built distribution metadata."""

import argparse
import ast
import subprocess
import tarfile
from email.parser import Parser
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def package_version():
    tree = ast.parse((ROOT / "src/smd_reports/__init__.py").read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__" for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError("Package version is missing")


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check(tag, *, check_git=False, dist=None):
    version = package_version()
    if tag != f"v{version}":
        raise ValueError("Release tag must match the package version exactly")
    if check_git:
        tagged = git("rev-parse", f"refs/tags/{tag}^{{commit}}")
        if tagged != git("rev-parse", "HEAD"):
            raise ValueError("The checkout must be the tagged release commit")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", tagged, "origin/master"], cwd=ROOT, check=True
        )
    if dist is not None:
        wheels, sources = list(dist.glob("*.whl")), list(dist.glob("*.tar.gz"))
        if len(wheels) != 1 or len(sources) != 1:
            raise ValueError("Release must contain exactly one wheel and one source distribution")
        with ZipFile(wheels[0]) as archive:
            name = next(path for path in archive.namelist() if path.endswith(".dist-info/METADATA"))
            metadata = Parser().parsestr(archive.read(name).decode())
            required = [
                "smd_reports/templates/components/grid.html",
                "smd_reports/static/fonts.css",
                "smd_reports/static/SourceSans3-LICENSE.md",
            ]
            if any(path not in archive.namelist() for path in required):
                raise ValueError("Wheel is missing rendering assets")
        with tarfile.open(sources[0]) as archive:
            member = next(path for path in archive.getnames() if path.endswith("/PKG-INFO"))
            source_metadata = Parser().parsestr(archive.extractfile(member).read().decode())
        for item in (metadata, source_metadata):
            if item["Name"] != "smd-reports" or item["Version"] != version:
                raise ValueError("Distribution name or version does not match the release")
            if not item.get_all("Project-URL") or not item.get("License-Expression"):
                raise ValueError("Distribution is missing public project metadata")
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()
    try:
        version = check(args.tag, check_git=args.check_git, dist=args.dist)
    except (ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Release check failed: {exc}") from exc
    print(f"Validated release {version}")


if __name__ == "__main__":
    main()
