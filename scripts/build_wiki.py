"""Prepare GitHub wiki pages from the MkDocs documentation."""

import argparse
import html
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import yaml
from yaml_env_tag import add_env_tag

ROOT = Path(__file__).resolve().parents[1]
# Retain published page URLs when MkDocs navigation labels differ.
PAGE_NAMES = {
    "index.md": "Home",
    "integration.md": "Report-examples",
    "reference.md": "Python-reference",
    "cli.md": "Command-line",
    "publishing.md": "Publishing",
}
LINK = re.compile(r"(!?)\[([^\]\n]*)\]\(([^\s)]+)(\s+[\"'][^\n]*?[\"'])?\)")
INLINE_CODE = re.compile(r"(`+).*?\1")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


class WikiConfigLoader(yaml.SafeLoader):
    """Load MkDocs environment tags without changing the global YAML loader."""


add_env_tag(WikiConfigLoader)


def navigation_pages(items):
    """Flatten the MkDocs navigation while retaining page labels.

    Args:
        items: MkDocs navigation entries, including nested groups.

    Yields:
        Pairs of page labels and source filenames.
    """
    for item in items:
        for title, target in item.items():
            if isinstance(target, list):
                yield from navigation_pages(target)
            else:
                yield title, target


def rewrite_links(text, source, pages, root, repository, revision):
    """Resolve Markdown links for the wiki while preserving code examples.

    Args:
        text: Original Markdown page.
        source: Source page path.
        pages: Source paths mapped to wiki page names.
        root: Source repository directory.
        repository: GitHub owner/repository name.
        revision: Full source commit hash used for asset URLs.

    Returns:
        Markdown with wiki page links and repository file/image URLs.

    Raises:
        ValueError: A relative link is missing, outside the repository or not in navigation.
    """
    base = f"https://github.com/{repository}"

    def replace(match):
        image, caption, target, title = match.groups()
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            return match[0]
        path = (source.parent / unquote(url.path)).resolve()
        if not path.is_relative_to(root) or not path.exists():
            raise ValueError(f"Broken documentation link in {source.relative_to(root)}: {target}")
        if path in pages:
            destination = f"{base}/wiki/{pages[path]}"
        elif path.suffix == ".md" and path.is_relative_to(root / "docs"):
            raise ValueError(f"Documentation page is missing from navigation: {target}")
        elif image:
            destination = f"https://raw.githubusercontent.com/{repository}/{revision}/"
            destination += quote(path.relative_to(root).as_posix())
        else:
            kind = "tree" if path.is_dir() else "blob"
            destination = f"{base}/{kind}/{revision}/{quote(path.relative_to(root).as_posix())}"
        if url.query:
            destination += "?" + url.query
        if url.fragment:
            destination += "#" + url.fragment
        return f"{image}[{caption}]({destination}{title or ''})"

    output = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = FENCE.match(line)
        if marker:
            value = marker[1]
            if fence is None:
                fence = value
            elif (
                value[0] == fence[0]
                and len(value) >= len(fence)
                and not line[marker.end() :].strip()
            ):
                fence = None
            output.append(line)
            continue
        if fence is not None:
            output.append(line)
            continue
        position = 0
        for code in INLINE_CODE.finditer(line):
            output.append(LINK.sub(replace, line[position : code.start()]))
            output.append(code[0])
            position = code.end()
        output.append(LINK.sub(replace, line[position:]))
    return "".join(output)


def build_wiki(root, output, repository, revision):
    """Generate wiki pages, navigation and footer into an empty directory.

    Args:
        root: Repository containing mkdocs.yml and docs/.
        output: Empty destination directory, separate from the source documentation.
        repository: GitHub owner/repository name.
        revision: Full source commit hash.

    Returns:
        Number of documentation pages generated, excluding sidebar and footer.

    Raises:
        ValueError: Configuration, source links or the destination are invalid.
        OSError: Source files cannot be read or output cannot be written.
    """
    root, output = Path(root).resolve(), Path(output).resolve()
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository):
        raise ValueError("Repository must have the form owner/name")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("Revision must be a full source commit hash")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Wiki output directory must be empty")
    config = yaml.load((root / "mkdocs.yml").read_text(encoding="utf-8"), Loader=WikiConfigLoader)
    pages = {}
    for label, filename in navigation_pages(config["nav"]):
        path = (root / "docs" / filename).resolve()
        if not path.is_relative_to(root / "docs") or not path.is_file():
            raise ValueError(f"Navigation page does not exist in docs/: {filename}")
        name = PAGE_NAMES.get(filename, re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-"))
        if not name or path in pages or name.casefold() in {p.casefold() for p in pages.values()}:
            raise ValueError(f"Duplicate or invalid wiki page: {filename}")
        pages[path] = name
    rendered = {
        f"{name}.md": rewrite_links(
            path.read_text(encoding="utf-8"), path, pages, root, repository, revision
        )
        for path, name in pages.items()
    }
    base = f"https://github.com/{repository}"

    def sidebar(items):
        lines = []
        for item in items:
            for title, target in item.items():
                if isinstance(target, list):
                    lines.extend([f"\n**{title}**\n\n", *sidebar(target)])
                else:
                    name = pages[(root / "docs" / target).resolve()]
                    lines.append(f"- [{title}]({base}/wiki/{name})\n")
        return lines

    rendered["_Sidebar.md"] = "".join(sidebar(config["nav"])).lstrip()
    copyright = html.unescape(config.get("copyright", ""))
    rendered["_Footer.md"] = f"{copyright}\n\n[Repository]({base}) · [Issues]({base}/issues)\n"
    output.mkdir(parents=True, exist_ok=True)
    for name, text in rendered.items():
        (output / name).write_text(text, encoding="utf-8")
    return len(pages)


def main():
    """Parse build options and prepare the documentation for wiki publishing."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()
    try:
        count = build_wiki(ROOT, args.output, args.repository, args.revision)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Wiki build failed: {exc}\n")
    print(f"Prepared {count} wiki pages")


if __name__ == "__main__":
    main()
