"""Release version progression, changelog content, tag ancestry and workflow guards."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "check_release", Path(__file__).parents[1] / "scripts/check_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required for ancestry checks")
def test_release_must_be_tagged_on_master(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=tmp_path, text=True, stderr=subprocess.DEVNULL
        ).strip()

    package = tmp_path / "src/smd_reports"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n')
    git("init", "--initial-branch=master")
    git("config", "user.name", "Synthetic release test")
    git("config", "user.email", "release-test@example.org")
    (tmp_path / "CHANGELOG.md").write_text("# Changelog\n\n## 0.1.0\n\n- Initial release.\n")
    git("add", "src", "CHANGELOG.md")
    git("commit", "-m", "Synthetic master")
    master = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/master", master)
    git("checkout", "-b", "feature")
    (tmp_path / "feature.txt").write_text("Synthetic feature\n")
    git("add", "feature.txt")
    git("commit", "-m", "Synthetic feature")
    git("tag", "v0.1.0")
    monkeypatch.setattr(release, "ROOT", tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        release.check("v0.1.0", check_git=True)
    git("tag", "-d", "v0.1.0")
    git("checkout", "master")
    git("tag", "v0.1.0")
    assert release.check("v0.1.0", check_git=True) == "0.1.0"
    with pytest.raises(ValueError, match="package version"):
        release.check("v9.9.9")


@pytest.fixture
def repository(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=tmp_path, text=True, stderr=subprocess.DEVNULL
        ).strip()

    git("init", "--initial-branch=master")
    git("config", "user.name", "Synthetic release test")
    git("config", "user.email", "release-test@example.org")
    (tmp_path / "README.md").write_text("# Synthetic repository\n")
    git("add", ".")
    git("commit", "-m", "Initial repository")
    monkeypatch.setattr(release, "ROOT", tmp_path)
    return tmp_path, git


def write_candidate(root, version, entry="- Added a report option."):
    package = root / "src/smd_reports"
    package.mkdir(parents=True, exist_ok=True)
    (package / "__init__.py").write_text(f'__version__ = "{version}"\n')
    (root / "CHANGELOG.md").write_text(f"# Changelog\n\n## {version}\n\n{entry}\n")


def baseline(repository, version="0.1.0"):
    root, git = repository
    write_candidate(root, version)
    git("add", ".")
    git("commit", "-m", "Previous release")
    git("tag", f"v{version}")
    git("update-ref", "refs/remotes/origin/master", git("rev-parse", "HEAD"))
    return git("rev-parse", "HEAD")


@pytest.mark.parametrize("candidate", ["0.1.0", "0.0.9"])
def test_release_pr_requires_version_increase(repository, candidate):
    root, _ = repository
    base = baseline(repository)
    write_candidate(root, candidate)
    with pytest.raises(ValueError, match="newer than master version 0.1.0"):
        release.check_candidate(base)


def test_release_pr_uses_numeric_versions_and_exact_base_commit(repository):
    root, git = repository
    base = baseline(repository, "0.1.9")
    write_candidate(root, "0.1.10")
    git("add", ".")
    git("commit", "-m", "Candidate release")
    assert release.check_candidate(base) == "0.1.10"
    # A moving branch is different from the exact PR base commit.
    with pytest.raises(ValueError, match="newer than master version"):
        release.check_candidate("master")


def test_first_release_without_package_or_tags_on_base(repository):
    root, git = repository
    base = git("rev-parse", "HEAD")
    write_candidate(root, "0.1.0")
    assert release.check_candidate(base) == "0.1.0"


def test_release_pr_checks_previous_tags_as_well_as_base_version(repository):
    root, git = repository
    base = baseline(repository)
    git("tag", "v0.2.0")
    write_candidate(root, "0.1.1")
    with pytest.raises(ValueError, match="newer than released version 0.2.0"):
        release.check_candidate(base)


def test_unmerged_and_nonversion_tags_do_not_block_release(repository):
    root, git = repository
    base = baseline(repository)
    git("tag", "v-not-a-version")
    git("checkout", "-b", "future-work")
    (root / "future.txt").write_text("Future work\n")
    git("add", ".")
    git("commit", "-m", "Unmerged work")
    git("tag", "v99.0.0")
    git("checkout", "master")
    write_candidate(root, "0.1.1")
    assert release.check_candidate(base) == "0.1.1"


def test_publishing_excludes_candidate_tag_but_checks_previous_releases(repository):
    root, git = repository
    baseline(repository)
    write_candidate(root, "0.2.0")
    git("add", ".")
    git("commit", "-m", "Candidate release")
    git("update-ref", "refs/remotes/origin/master", git("rev-parse", "HEAD"))
    git("tag", "-a", "v0.2.0", "-m", "Candidate release")
    assert release.check("v0.2.0", check_git=True) == "0.2.0"
    git("tag", "v0.3.0")
    with pytest.raises(ValueError, match="newer than released version 0.3.0"):
        release.check("v0.2.0", check_git=True)


@pytest.mark.parametrize(
    "text",
    [
        "# Changelog\n\n## 0.1.0\n\n- Previous release.\n",
        "# Changelog\n\n## 0.2.0\n\n## 0.1.0\n\n- Previous release.\n",
        "## 0.2.0\n\n### Added\n\n### Fixed\n",
        "## 0.2.0\n\n<!-- Details will be added later. -->\n",
        "## 0.2.0\n\n- TBD\n",
        "## 0.2.0\n\n---\n\n[0.2.0]: https://example.org/releases\n",
        "## 0.2.0\n\n- Added a table.\n\n## 0.2.0\n\n- Duplicate entry.\n",
        "<!--\n## 0.2.0\n\n- Hidden entry.\n-->\n",
        "```markdown\n## 0.2.0\n\n- Example only.\n```\n",
    ],
)
def test_changelog_rejects_missing_empty_or_duplicate_release_entries(repository, text):
    root, _ = repository
    write_candidate(root, "0.2.0")
    (root / "CHANGELOG.md").write_text(text)
    with pytest.raises(ValueError, match="CHANGELOG.md"):
        release.check("v0.2.0")


def test_missing_changelog_blocks_publication(repository):
    root, _ = repository
    write_candidate(root, "0.2.0")
    (root / "CHANGELOG.md").unlink()
    with pytest.raises(ValueError, match="CHANGELOG.md is required"):
        release.check("v0.2.0")


def test_changelog_accepts_dated_entries_and_ignores_examples(repository):
    root, _ = repository
    write_candidate(root, "0.2.0")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n## [0.2.0] - 2026-11-08\n\n"
        "### Added\n\n- Added dynamic report columns.\n\n"
        "```markdown\n## 0.2.0\n- Example header.\n```\n\n"
        "## 0.1.0\n\n- First release.\n"
    )
    assert release.check("v0.2.0") == "0.2.0"


@pytest.mark.parametrize(
    "source",
    [
        '__version__ = "not-a-version"',
        "__version__ = 1",
        '__version__ = "unterminated',
        'name = "missing-version"',
    ],
)
def test_package_version_rejects_invalid_declarations_without_import(source):
    with pytest.raises(ValueError, match="version"):
        release.package_version(source)


def test_release_checks_are_part_of_required_branch_flow_job():
    import yaml

    root = Path(__file__).parents[1]
    workflow = yaml.load(
        (root / ".github/workflows/pr-target.yml").read_text(), Loader=yaml.BaseLoader
    )
    job = workflow["jobs"]["branch-flow"]
    assert job["env"]["BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    check = next(
        step for step in job["steps"] if step.get("name") == "Check release version and changelog"
    )
    assert check["if"] == "github.base_ref == 'master'"
    assert check["run"] == 'python scripts/check_release.py --base-ref "$BASE_SHA"'
    checkout = next(
        step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")
    )
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha }}"
    assert checkout["with"]["fetch-depth"] == "0"
    publish = yaml.load(
        (root / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert any("--check-git" in step.get("run", "") for step in publish["jobs"]["build"]["steps"])
