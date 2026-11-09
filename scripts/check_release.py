"""Validate release versions, changelog entries, tags and distribution metadata."""

import argparse
import ast
import re
import subprocess
import tarfile
from email.parser import Parser
from pathlib import Path
from zipfile import ZipFile

from packaging.version import InvalidVersion, Version

ROOT = Path(__file__).resolve().parents[1]


def package_version(source=None):
    """Read the package version without importing or executing package code.

    Args:
        source: Optional Python source from a comparison commit. None reads the checkout.

    Returns:
        The declared package version.

    Raises:
        ValueError: The declaration is missing, invalid or not a literal version string.
    """
    if source is None:
        source = (ROOT / "src/smd_reports/__init__.py").read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "__version__"
                for target in node.targets
            ):
                version = ast.literal_eval(node.value)
                if not isinstance(version, str):
                    raise ValueError("Package version must be a literal string")
                Version(version)
                return version
    except (SyntaxError, InvalidVersion) as exc:
        raise ValueError("Package version must be a valid Python packaging version") from exc
    raise ValueError("Package version is missing")


def git(*args):
    """Run a read-only Git query in the source checkout.

    Args:
        *args: Git subcommand and arguments.

    Returns:
        Standard output with surrounding whitespace removed.

    Raises:
        subprocess.CalledProcessError: Git rejects the query.
    """
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def check_changelog(version):
    """Require exactly one nonempty changelog entry for the candidate version.

    Args:
        version: Version string declared by the package.

    Raises:
        ValueError: The changelog or its release entry is missing, duplicated or empty.
    """
    path = ROOT / "CHANGELOG.md"
    if not path.is_file():
        raise ValueError("CHANGELOG.md is required for a release")
    text = re.sub(r"<!--.*?-->", "", path.read_text(encoding="utf-8"), flags=re.DOTALL)
    lines = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif (
                marker[1][0] == fence[0]
                and len(marker[1]) >= len(fence)
                and not line[marker.end() :].strip()
            ):
                fence = None
        elif fence is None:
            lines.append(line)
    text = "\n".join(lines)
    headings = list(re.finditer(r"^##[ \t]+(.+?)\s*$", text, re.MULTILINE))
    matching = []
    for index, heading in enumerate(headings):
        name = re.fullmatch(
            r"(?:\[([^]\n]+)\]|(\S+))(?:[ \t]+-[ \t]+\d{4}-\d{2}-\d{2})?",
            heading[1],
        )
        if name and (name[1] or name[2]) == version:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
            matching.append(text[heading.end() : end])
    if len(matching) != 1:
        raise ValueError(f"CHANGELOG.md must contain exactly one '## {version}' release entry")
    entry = matching[0]
    content = []
    for line in entry.splitlines():
        line = line.strip()
        if re.match(r"^(?:#{1,6}(?:\s|$)|\[[^]]+\]:)", line):
            continue
        if re.fullmatch(r"(?:[-*_][ \t]*){3,}", line):
            continue
        line = re.sub(r"^[-*+]\s*", "", line).strip()
        if line and not re.fullmatch(r"(?i)(?:tbd|todo|pending)[.!:]?", line):
            content.append(line)
    if not content:
        raise ValueError(f"CHANGELOG.md entry for {version} must describe the release changes")


def check_version_progression(version, reference, *, exclude_tag=None):
    """Require the candidate to be newer than release tags reachable from a commit.

    Args:
        version: Candidate package version.
        reference: Commit or branch containing previous releases.
        exclude_tag: Candidate's own tag during publication, which is not a previous release.

    Raises:
        ValueError: A previous release has the same or a higher version.
        subprocess.CalledProcessError: Git cannot inspect the comparison reference.
    """
    previous = []
    for tag in git("tag", "--list", "v*", "--merged", reference).splitlines():
        if tag == exclude_tag:
            continue
        try:
            previous.append(Version(tag[1:]))
        except InvalidVersion:
            continue
    if previous and Version(version) <= max(previous):
        raise ValueError(
            f"Package version {version} must be newer than released version {max(previous)}"
        )


def check_candidate(base_ref):
    """Check version progression and release notes before merging a release PR.

    Args:
        base_ref: Exact base commit supplied by the pull request event.

    Returns:
        The validated candidate version.

    Raises:
        ValueError: Version progression or changelog validation fails.
        subprocess.CalledProcessError: Git cannot inspect the comparison commit.
    """
    version = package_version()
    git("rev-parse", "--verify", f"{base_ref}^{{commit}}")
    filename = "src/smd_reports/__init__.py"
    if git("ls-tree", "--name-only", base_ref, "--", filename):
        previous = package_version(git("show", f"{base_ref}:{filename}"))
        if Version(version) <= Version(previous):
            raise ValueError(
                f"Package version {version} must be newer than master version {previous}"
            )
    check_version_progression(version, base_ref)
    check_changelog(version)
    return version


def check(tag, *, check_git=False, dist=None):
    """Validate a release tag and optionally inspect ancestry and distributions.

    Args:
        tag: Expected version tag, including its v prefix.
        check_git: Verify tag ancestry and version progression against previous release tags.
        dist: Optional directory containing one wheel and one source archive.

    Returns:
        The validated package version.

    Raises:
        ValueError: Release notes, version progression, tag or distribution metadata is invalid.
        subprocess.CalledProcessError: The tag is absent or fails the ancestry check.
    """
    version = package_version()
    if tag != f"v{version}":
        raise ValueError("Release tag must match the package version exactly")
    check_changelog(version)
    if check_git:
        tagged = git("rev-parse", f"refs/tags/{tag}^{{commit}}")
        if tagged != git("rev-parse", "HEAD"):
            raise ValueError("The checkout must be the tagged release commit")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", tagged, "origin/master"], cwd=ROOT, check=True
        )
        check_version_progression(version, "origin/master", exclude_tag=tag)
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
    """Validate the release requested through the command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", nargs="?")
    parser.add_argument("--base-ref", help="Validate a release PR against its exact base commit")
    parser.add_argument("--check-git", action="store_true")
    parser.add_argument("--dist", type=Path)
    args = parser.parse_args()
    if args.base_ref:
        if args.tag or args.check_git or args.dist:
            parser.error("--base-ref cannot be combined with a tag, --check-git or --dist")
    elif args.tag is None:
        parser.error("supply a release tag or --base-ref")
    try:
        version = (
            check_candidate(args.base_ref)
            if args.base_ref
            else check(args.tag, check_git=args.check_git, dist=args.dist)
        )
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"Release check failed: {exc}") from exc
    print(f"Validated release {version}")


if __name__ == "__main__":
    main()
