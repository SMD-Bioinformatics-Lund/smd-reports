"""Wiki page generation, link conversion and publishing branch restrictions."""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("build_wiki", ROOT / "scripts/build_wiki.py")
wiki = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(wiki)
REPOSITORY = "example/reports"
REVISION = "a" * 40


@pytest.fixture
def source(tmp_path):
    root = tmp_path / "repository"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (root / "mkdocs.yml").write_text(
        "copyright: Copyright &copy; Example\nnav:\n"
        "  - Overview: index.md\n  - Guide:\n    - Installation: installation.md\n"
    )
    (docs / "index.md").write_text("# Overview\n\n[Install](installation.md#setup)\n")
    (docs / "installation.md").write_text("# Installation\n")
    return root


def build(source, tmp_path, name="wiki"):
    output = tmp_path / name
    count = wiki.build_wiki(source, output, REPOSITORY, REVISION)
    return count, output


def test_builds_all_current_pages_and_preserves_existing_urls(tmp_path):
    count, output = build(ROOT, tmp_path)
    published = {path.name for path in output.glob("*.md")}
    assert count == 13
    assert {
        "Home.md",
        "Python-usage.md",
        "Python-reference.md",
        "Report-examples.md",
        "Command-line.md",
        "Publishing.md",
        "_Sidebar.md",
        "_Footer.md",
    } <= published
    assert len(published) == count + 2
    home = (output / "Home.md").read_text()
    assert f"https://github.com/{REPOSITORY}/wiki/Installation" in home
    assert f"https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}/docs/assets/" in home
    assert "(assets/" not in home
    sidebar = (output / "_Sidebar.md").read_text()
    assert sidebar.count(f"https://github.com/{REPOSITORY}/wiki/") == count
    assert "**User guide**" in sidebar and "**Development**" in sidebar
    assert "Ram Nanduri" in (output / "_Footer.md").read_text()


def test_relative_links_assets_anchors_and_code_examples(source, tmp_path):
    docs = source / "docs"
    (docs / "assets").mkdir()
    (docs / "assets/plot.svg").write_text("<svg/>")
    (source / "example.json").write_text("{}")
    text = """[Guide](installation.md#setup)
![Plot](assets/plot.svg "Diagram")
[Data](../example.json)
[Section](#overview) [External](https://example.org/page) [Mail](mailto:a@example.org)
`[literal](missing.md)` and [Guide](installation.md)
```markdown
[Example](missing.md)
```
~~~
![Example](missing.svg)
~~~
"""
    (docs / "index.md").write_text(text)
    _, output = build(source, tmp_path)
    home = (output / "Home.md").read_text()
    assert f"[Guide](https://github.com/{REPOSITORY}/wiki/Installation#setup)" in home
    asset = f"https://raw.githubusercontent.com/{REPOSITORY}/{REVISION}/docs/assets/plot.svg"
    assert f'![Plot]({asset} "Diagram")' in home
    assert f"[Data](https://github.com/{REPOSITORY}/blob/{REVISION}/example.json)" in home
    assert "[Section](#overview)" in home and "[Mail](mailto:a@example.org)" in home
    assert "[External](https://example.org/page)" in home
    assert "`[literal](missing.md)`" in home
    assert "```markdown\n[Example](missing.md)\n```" in home
    assert "~~~\n![Example](missing.svg)\n~~~" in home


@pytest.mark.parametrize("target", ["missing.md", "../outside/absent.svg"])
def test_broken_links_fail_before_writing_pages(source, tmp_path, target):
    (source / "docs/index.md").write_text(f"[Broken]({target})")
    with pytest.raises(ValueError, match="Broken documentation link"):
        build(source, tmp_path)
    assert not (tmp_path / "wiki").exists()


def test_new_navigation_pages_are_added_without_script_changes(source, tmp_path):
    config = source / "mkdocs.yml"
    config.write_text(config.read_text() + "    - Another guide: another.md\n")
    (source / "docs/another.md").write_text("# Another guide\n")
    count, output = build(source, tmp_path)
    assert count == 3 and (output / "Another-guide.md").is_file()
    assert "Another-guide" in (output / "_Sidebar.md").read_text()


def test_unlisted_doc_pages_and_duplicate_page_names_are_rejected(source, tmp_path):
    (source / "docs/unlisted.md").write_text("# Missing navigation\n")
    (source / "docs/index.md").write_text("[Page](unlisted.md)")
    with pytest.raises(ValueError, match="missing from navigation"):
        build(source, tmp_path)
    (source / "docs/index.md").write_text("# Overview\n")
    config = source / "mkdocs.yml"
    config.write_text(config.read_text() + "    - Installation: unlisted.md\n")
    with pytest.raises(ValueError, match="Duplicate or invalid"):
        build(source, tmp_path)


def test_generation_is_deterministic_and_keeps_existing_output(source, tmp_path):
    _, first = build(source, tmp_path, "first")
    _, second = build(source, tmp_path, "second")

    def contents(path):
        return {page.name: page.read_bytes() for page in path.iterdir()}

    assert contents(first) == contents(second)
    before = contents(first)
    with pytest.raises(ValueError, match="must be empty"):
        build(source, tmp_path, "first")
    assert contents(first) == before


def test_publishing_is_restricted_to_master_and_ci_checks_generated_pages():
    workflow = yaml.load((ROOT / ".github/workflows/wiki.yml").read_text(), Loader=yaml.BaseLoader)
    assert workflow["on"]["push"]["branches"] == ["master"]
    assert "pull_request" not in workflow["on"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["jobs"]["publish"]["if"] == "github.ref == 'refs/heads/master'"
    assert workflow["permissions"] == {"contents": "write"}
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    ci = yaml.load((ROOT / ".github/workflows/quality.yml").read_text(), Loader=yaml.BaseLoader)
    assert any(
        "scripts/build_wiki.py" in step.get("run", "") for step in ci["jobs"]["docs"]["steps"]
    )
